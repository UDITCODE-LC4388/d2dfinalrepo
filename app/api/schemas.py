from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RepositoryCreateRequest(BaseModel):
    repo_url: str = Field(..., description="Remote Git URL or absolute/local filesystem path.")
    display_name: str | None = Field(default=None)
    branch: str | None = Field(default=None)
    max_commits: int = Field(default=500, ge=1, le=10_000)
    force_reanalyze: bool = Field(default=False)


class RepositorySyncRequest(BaseModel):
    branch: str | None = None
    max_commits: int | None = Field(default=None, ge=1, le=10_000)
    force_reanalyze: bool = False


class RepositoryResponse(BaseModel):
    id: str
    display_name: str
    repo_url: str
    default_branch: str | None = None
    status: str
    last_synced_at: datetime | None = None
    last_analyzed_commit: str | None = None
    max_commits: int
    created_at: datetime
    updated_at: datetime


class JobResponse(BaseModel):
    id: str
    repo_id: str
    job_type: str
    status: str
    progress: float
    message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class RepositoryCreateResponse(BaseModel):
    repository: RepositoryResponse
    job: JobResponse


class CommitFileResponse(BaseModel):
    path: str
    old_path: str | None = None
    change_type: str
    language: str
    additions: int
    deletions: int
    complexity_before: float
    complexity_after: float
    symbols_before: int
    symbols_after: int
    import_count_before: int
    import_count_after: int


class CommitResponse(BaseModel):
    sha: str
    commit_index: int
    author_name: str
    author_email: str
    authored_at: datetime
    message: str
    parent_count: int
    files_changed: int
    additions: int
    deletions: int
    risk_score: float
    hotspot_score: float
    complexity_delta: float
    ownership_entropy: float
    primary_language: str


class CommitDetailResponse(CommitResponse):
    files: list[CommitFileResponse]


class HotspotResponse(BaseModel):
    path: str
    language: str
    churn: int
    complexity: float
    contributors: int
    ownership_entropy: float
    hotspot_score: float
    last_commit_sha: str | None = None


class MetricPointResponse(BaseModel):
    commit_sha: str
    commit_index: int
    metric_key: str
    value: float
    measured_at: datetime


class DependencyEdgeResponse(BaseModel):
    source_path: str
    target_path: str
    edge_type: str
    strength: float
    last_seen_commit_sha: str | None = None


class HealthSummaryResponse(BaseModel):
    repo_id: str
    health_index: float
    code_health: float
    team_health: float
    architecture_health: float
    temporal_health: float
    total_commits: int
    active_files: int
    languages: dict[str, int]
    top_risks: list[str]
    metrics: dict[str, float]


class ContributorSummaryResponse(BaseModel):
    author_name: str
    author_email: str
    commit_count: int
    total_churn: int
    average_commit_risk: float


class ArchitectureSummaryResponse(BaseModel):
    dependency_edges: int
    cyclic_dependencies: int
    coupling_score: float
    instability_score: float


class RepositoryExecutiveSummaryResponse(BaseModel):
    repository: RepositoryResponse
    latest_job: JobResponse | None = None
    health: HealthSummaryResponse | None = None
    architecture: ArchitectureSummaryResponse | None = None
    top_hotspots: list[HotspotResponse]
    riskiest_commits: list[CommitResponse]
    top_contributors: list[ContributorSummaryResponse]
    recommendations: list[str]


class RepositoryOverviewResponse(BaseModel):
    repository: RepositoryResponse
    latest_job: JobResponse | None = None
    health: HealthSummaryResponse | None = None


class PaginatedCommitResponse(BaseModel):
    items: list[CommitResponse]
    total: int
    limit: int
    offset: int


class GenericMessageResponse(BaseModel):
    message: str
    details: dict[str, Any] | None = None
