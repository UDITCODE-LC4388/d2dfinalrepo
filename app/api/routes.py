from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.schemas import (
    ArchitectureSummaryResponse,
    CommitDetailResponse,
    CommitResponse,
    ContributorSummaryResponse,
    DependencyEdgeResponse,
    GenericMessageResponse,
    HealthSummaryResponse,
    HotspotResponse,
    JobResponse,
    MetricPointResponse,
    PaginatedCommitResponse,
    RepositoryCreateRequest,
    RepositoryCreateResponse,
    RepositoryExecutiveSummaryResponse,
    RepositoryOverviewResponse,
    RepositoryResponse,
    RepositorySyncRequest,
)


router = APIRouter()


def _database(request: Request):
    return request.app.state.database


def _runner(request: Request):
    return request.app.state.job_runner


def _ensure_repository(request: Request, repo_id: str) -> dict:
    repository = _database(request).get_repository(repo_id)
    if repository is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")
    return repository


@router.get("/healthz", response_model=GenericMessageResponse, tags=["system"])
async def healthcheck() -> GenericMessageResponse:
    return GenericMessageResponse(message="ok", details={"service": "repository-health-intelligence"})


@router.get("/", response_model=GenericMessageResponse, tags=["system"])
async def root(request: Request) -> GenericMessageResponse:
    repositories = _database(request).list_repositories()
    ready_count = sum(1 for repository in repositories if repository["status"] == "ready")
    return GenericMessageResponse(
        message="Repository Health Intelligence API is running.",
        details={
            "healthcheck": "/healthz",
            "docs": "/docs",
            "repositories": "/v1/repositories",
            "repository_count": len(repositories),
            "ready_repositories": ready_count,
        },
    )


@router.get("/v1/repositories", response_model=list[RepositoryOverviewResponse], tags=["repositories"])
async def list_repositories(request: Request) -> list[RepositoryOverviewResponse]:
    database = _database(request)
    repositories = database.list_repositories()
    return [
        RepositoryOverviewResponse(
            repository=RepositoryResponse.model_validate(repository),
            latest_job=JobResponse.model_validate(job) if (job := database.get_latest_job_for_repo(repository["id"])) else None,
            health=_build_health_summary(database, repository["id"]),
        )
        for repository in repositories
    ]


@router.post(
    "/v1/repositories",
    response_model=RepositoryCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["repositories"],
)
async def create_repository(request: Request, payload: RepositoryCreateRequest) -> RepositoryCreateResponse:
    database = _database(request)
    runner = _runner(request)
    normalized_repo_url = _normalize_repo_url(payload.repo_url)
    _validate_repo_target(normalized_repo_url)
    existing = database.find_repository_by_url(normalized_repo_url)
    if existing is not None:
        update_fields = {"max_commits": payload.max_commits}
        if payload.display_name:
            update_fields["display_name"] = payload.display_name
        if payload.branch:
            update_fields["default_branch"] = payload.branch
        existing = database.update_repository(existing["id"], **update_fields)
        try:
            job = await runner.schedule_repository_sync(
                repo_id=existing["id"],
                branch=payload.branch,
                max_commits=payload.max_commits,
                force_reanalyze=payload.force_reanalyze,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return RepositoryCreateResponse(
            repository=RepositoryResponse.model_validate(existing),
            job=JobResponse.model_validate(job),
        )

    display_name = payload.display_name or _infer_display_name(normalized_repo_url)
    repo_id_hint = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    clone_path = str(Path(request.app.state.job_runner.settings.clone_dir) / repo_id_hint)
    repository = database.create_repository(
        display_name=display_name,
        repo_url=normalized_repo_url,
        clone_path=clone_path,
        default_branch=payload.branch,
        max_commits=payload.max_commits,
    )
    repository = database.update_repository(
        repository["id"],
        clone_path=str(Path(request.app.state.job_runner.settings.clone_dir) / repository["id"]),
    )
    try:
        job = await runner.schedule_repository_sync(
            repo_id=repository["id"],
            branch=payload.branch,
            max_commits=payload.max_commits,
            force_reanalyze=payload.force_reanalyze,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return RepositoryCreateResponse(
        repository=RepositoryResponse.model_validate(repository),
        job=JobResponse.model_validate(job),
    )


@router.get("/v1/repositories/{repo_id}", response_model=RepositoryOverviewResponse, tags=["repositories"])
async def get_repository(request: Request, repo_id: str) -> RepositoryOverviewResponse:
    database = _database(request)
    repository = _ensure_repository(request, repo_id)
    latest_job = database.get_latest_job_for_repo(repo_id)
    health = _build_health_summary(database, repo_id)
    return RepositoryOverviewResponse(
        repository=RepositoryResponse.model_validate(repository),
        latest_job=JobResponse.model_validate(latest_job) if latest_job else None,
        health=health,
    )


@router.post(
    "/v1/repositories/{repo_id}/sync",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["repositories"],
)
async def sync_repository(request: Request, repo_id: str, payload: RepositorySyncRequest) -> JobResponse:
    repository = _ensure_repository(request, repo_id)
    update_fields = {}
    if payload.max_commits is not None:
        update_fields["max_commits"] = payload.max_commits
    if payload.branch:
        update_fields["default_branch"] = payload.branch
    if update_fields:
        repository = _database(request).update_repository(repository["id"], **update_fields)
    try:
        job = await _runner(request).schedule_repository_sync(
            repo_id=repo_id,
            branch=payload.branch,
            max_commits=payload.max_commits,
            force_reanalyze=payload.force_reanalyze,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return JobResponse.model_validate(job)


@router.get("/v1/jobs/{job_id}", response_model=JobResponse, tags=["repositories"])
async def get_job(request: Request, job_id: str) -> JobResponse:
    job = _database(request).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return JobResponse.model_validate(job)


@router.get("/v1/repositories/{repo_id}/commits", response_model=PaginatedCommitResponse, tags=["analysis"])
async def list_commits(
    request: Request,
    repo_id: str,
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> PaginatedCommitResponse:
    _ensure_repository(request, repo_id)
    total, rows = _database(request).list_commits(repo_id, limit=limit, offset=offset)
    return PaginatedCommitResponse(
        items=[CommitResponse.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/v1/repositories/{repo_id}/commits/{sha}", response_model=CommitDetailResponse, tags=["analysis"])
async def get_commit(request: Request, repo_id: str, sha: str) -> CommitDetailResponse:
    _ensure_repository(request, repo_id)
    database = _database(request)
    commit = database.get_commit(repo_id, sha)
    if commit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commit not found.")
    files = database.list_commit_files(repo_id, sha)
    return CommitDetailResponse.model_validate({**commit, "files": files})


@router.get("/v1/repositories/{repo_id}/hotspots", response_model=list[HotspotResponse], tags=["analysis"])
async def list_hotspots(
    request: Request,
    repo_id: str,
    limit: int = Query(default=25, ge=1, le=200),
) -> list[HotspotResponse]:
    _ensure_repository(request, repo_id)
    rows = _database(request).list_hotspots(repo_id, limit=limit)
    return [HotspotResponse.model_validate(row) for row in rows]


@router.get("/v1/repositories/{repo_id}/metrics/{metric_key}", response_model=list[MetricPointResponse], tags=["analysis"])
async def get_metric_timeline(
    request: Request,
    repo_id: str,
    metric_key: str,
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[MetricPointResponse]:
    _ensure_repository(request, repo_id)
    rows = _database(request).list_metric_timeline(repo_id, metric_key, limit=limit)
    return [MetricPointResponse.model_validate(row) for row in rows]


@router.get("/v1/repositories/{repo_id}/dependencies", response_model=list[DependencyEdgeResponse], tags=["analysis"])
async def list_dependencies(
    request: Request,
    repo_id: str,
    limit: int = Query(default=250, ge=1, le=2000),
) -> list[DependencyEdgeResponse]:
    _ensure_repository(request, repo_id)
    rows = _database(request).list_dependency_edges(repo_id, limit=limit)
    normalized = [
        {
            "source_path": row["source_path"],
            "target_path": row["target_path"],
            "edge_type": row["edge_type"],
            "strength": row["strength"],
            "last_seen_commit_sha": row["last_seen_commit_sha"],
        }
        for row in rows
    ]
    return [DependencyEdgeResponse.model_validate(row) for row in normalized]


@router.get("/v1/repositories/{repo_id}/summary", response_model=RepositoryExecutiveSummaryResponse, tags=["repositories"])
async def get_repository_summary(request: Request, repo_id: str) -> RepositoryExecutiveSummaryResponse:
    database = _database(request)
    repository = _ensure_repository(request, repo_id)
    health = _build_health_summary(database, repo_id)
    latest_job = database.get_latest_job_for_repo(repo_id)
    metrics = database.get_repo_metrics(repo_id)
    top_hotspots = [HotspotResponse.model_validate(row) for row in database.list_hotspots(repo_id, limit=5)]
    riskiest_commits = [CommitResponse.model_validate(row) for row in database.list_riskiest_commits(repo_id, limit=5)]
    top_contributors = [
        ContributorSummaryResponse.model_validate(row)
        for row in database.list_top_contributors(repo_id, limit=5)
    ]
    architecture = None
    if metrics:
        architecture = ArchitectureSummaryResponse(
            dependency_edges=int(metrics.get("dependency_edges", {}).get("value", 0.0)),
            cyclic_dependencies=int(metrics.get("cyclic_dependencies", {}).get("value", 0.0)),
            coupling_score=float(metrics.get("coupling_score", {}).get("value", 0.0)),
            instability_score=float(metrics.get("instability_score", {}).get("value", 0.0)),
        )
    recommendations = _build_recommendations(metrics, top_hotspots, top_contributors)
    return RepositoryExecutiveSummaryResponse(
        repository=RepositoryResponse.model_validate(repository),
        latest_job=JobResponse.model_validate(latest_job) if latest_job else None,
        health=health,
        architecture=architecture,
        top_hotspots=top_hotspots,
        riskiest_commits=riskiest_commits,
        top_contributors=top_contributors,
        recommendations=recommendations,
    )


@router.get("/v1/repositories/{repo_id}/health", response_model=HealthSummaryResponse, tags=["analysis"])
async def get_health_summary(request: Request, repo_id: str) -> HealthSummaryResponse:
    _ensure_repository(request, repo_id)
    health = _build_health_summary(_database(request), repo_id)
    if health is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No health summary found. Trigger a repository sync first.",
        )
    return health


def _build_health_summary(database, repo_id: str) -> HealthSummaryResponse | None:
    metrics = database.get_repo_metrics(repo_id)
    if not metrics:
        return None
    health_payload = metrics.get("health_index", {}).get("payload", {})
    return HealthSummaryResponse(
        repo_id=repo_id,
        health_index=float(metrics.get("health_index", {}).get("value", 0.0)),
        code_health=float(metrics.get("code_health", {}).get("value", 0.0)),
        team_health=float(metrics.get("team_health", {}).get("value", 0.0)),
        architecture_health=float(metrics.get("architecture_health", {}).get("value", 0.0)),
        temporal_health=float(metrics.get("temporal_health", {}).get("value", 0.0)),
        total_commits=int(metrics.get("total_commits", {}).get("value", 0.0)),
        active_files=int(metrics.get("active_files", {}).get("value", 0.0)),
        languages=health_payload.get("languages", {}),
        top_risks=health_payload.get("top_risks", []),
        metrics={key: float(value["value"]) for key, value in metrics.items()},
    )


def _infer_display_name(repo_url: str) -> str:
    if repo_url.endswith(".git"):
        repo_url = repo_url[:-4]
    return Path(repo_url).name or "repository"


def _normalize_repo_url(repo_url: str) -> str:
    candidate = Path(repo_url).expanduser()
    if candidate.exists():
        return str(candidate.resolve())
    return repo_url.strip()


def _validate_repo_target(repo_url: str) -> None:
    candidate = Path(repo_url).expanduser()
    if candidate.exists():
        if not candidate.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Local repository path must be a directory.",
            )
        if not ((candidate / ".git").exists() or (candidate / "HEAD").exists()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Local path exists but does not look like a Git repository.",
            )
        return

    if repo_url.startswith(("http://", "https://", "git@", "ssh://", "file://")):
        return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Repository target must be a valid local Git path or remote Git URL.",
    )


def _build_recommendations(
    metrics: dict[str, dict],
    top_hotspots: list[HotspotResponse],
    top_contributors: list[ContributorSummaryResponse],
) -> list[str]:
    if not metrics:
        return [
            "Run a repository sync first to generate hotspots, dependency edges, and health metrics."
        ]

    recommendations: list[str] = []
    bus_factor = float(metrics.get("bus_factor", {}).get("value", 0.0))
    avg_hotspot = float(metrics.get("avg_hotspot_score", {}).get("value", 0.0))
    avg_commit_risk = float(metrics.get("avg_commit_risk", {}).get("value", 0.0))
    cycles = int(metrics.get("cyclic_dependencies", {}).get("value", 0.0))
    instability = float(metrics.get("instability_score", {}).get("value", 0.0))

    if bus_factor < 3:
        recommendations.append("Raise bus factor by spreading ownership across the hottest modules and rotating reviewers.")
    if avg_hotspot >= 8 and top_hotspots:
        recommendations.append(
            f"Start with hotspot reduction in `{top_hotspots[0].path}` and the other top-churn files before adding new features."
        )
    if cycles > 0:
        recommendations.append("Break cyclic imports in the dependency graph to reduce architectural fragility and change blast radius.")
    if instability >= 0.6:
        recommendations.append("High instability suggests fragile module boundaries; stabilize core modules before widening dependencies.")
    if avg_commit_risk >= 45:
        recommendations.append("Recent changes are landing with elevated risk; reduce batch size and require tighter pre-merge checks.")
    if top_contributors and bus_factor >= 3 and avg_hotspot < 8 and cycles == 0:
        recommendations.append("Repository health is stable; next step is deeper semantic analysis or PR risk prediction on top of this baseline.")
    if not recommendations:
        recommendations.append("Repository health looks balanced; keep watching trend metrics and hotspot churn as commit volume grows.")
    return recommendations[:5]
