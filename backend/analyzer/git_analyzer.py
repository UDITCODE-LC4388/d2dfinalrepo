import logging
import shutil
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from analyzer.ai_summary import AISummaryError, generate_summary
from analyzer.config import (
    DATA_DIR,
    FAST_LOG_THRESHOLD,
    GRAPH_NODE_WARN_THRESHOLD,
    MAX_COMMITS_HARD_CAP,
    PROGRESS_LOG_EVERY,
)

_LOG_FIELD_SEP = "\x1f"
from analyzer.graph_builder import build_graph
from analyzer.health_score import calculate_health

logger = logging.getLogger(__name__)

MAX_REPO_URL_LENGTH = 500


class RepoAnalysisError(Exception):
    pass


def _parse_repo_name(repo_url: str) -> str:
    url = repo_url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    name = url.split("/")[-1]
    if not name:
        raise RepoAnalysisError("Could not determine repository name from URL")
    return name


def _validate_repo_url(repo_url: str) -> str:
    if not repo_url or not repo_url.strip():
        raise RepoAnalysisError("repo_url is required")

    repo_url = repo_url.strip()
    if len(repo_url) > MAX_REPO_URL_LENGTH:
        raise RepoAnalysisError("repo_url is too long")

    parsed = urlparse(repo_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise RepoAnalysisError("repo_url must be a valid http(s) URL")

    return repo_url


def _commit_stats(commit) -> dict:
    try:
        stats = commit.stats
        return {
            "files_changed": len(stats.files),
            "insertions": stats.total.get("insertions", 0),
            "deletions": stats.total.get("deletions", 0),
        }
    except Exception as exc:
        logger.warning("Could not read stats for %s: %s", commit.hexsha, exc)
        return {"files_changed": 0, "insertions": 0, "deletions": 0}


def _ensure_full_clone(repo_url: str, repo_path) -> Repo:
    if not repo_path.exists():
        last_error = None
        for attempt in range(2):
            try:
                logger.info("Cloning full repository history: %s", repo_url)
                Repo.clone_from(repo_url, repo_path, single_branch=True)
                last_error = None
                break
            except GitCommandError as exc:
                last_error = exc
                if repo_path.exists():
                    shutil.rmtree(repo_path, ignore_errors=True)
        if last_error is not None:
            raise RepoAnalysisError(f"Failed to clone repository: {last_error}") from last_error
    else:
        logger.info("Using cached clone at %s", repo_path)

    try:
        repo = Repo(repo_path)
    except InvalidGitRepositoryError as exc:
        raise RepoAnalysisError(f"Invalid git repository at {repo_path}") from exc

    try:
        is_shallow = repo.git.rev_parse("--is-shallow-repository").strip() == "true"
    except GitCommandError:
        is_shallow = False

    if is_shallow:
        logger.info("Shallow clone detected — fetching full history...")
        try:
            repo.git.fetch("--unshallow")
        except GitCommandError as exc:
            logger.warning("Unshallow failed, re-cloning: %s", exc)
            shutil.rmtree(repo_path, ignore_errors=True)
            Repo.clone_from(repo_url, repo_path, single_branch=True)
            repo = Repo(repo_path)

    return repo


def _parse_git_log_numstat(output: str) -> list:
    """Parse combined `git log --pretty --numstat` output."""
    commits = []
    current = None

    for line in output.splitlines():
        if _LOG_FIELD_SEP in line:
            parts = line.split(_LOG_FIELD_SEP, 3)
            if len(parts) == 4:
                if current:
                    current["health_score"] = calculate_health(current)
                    commits.append(current)
                try:
                    ts = datetime.fromtimestamp(int(parts[2]), tz=timezone.utc).isoformat()
                except (ValueError, OSError):
                    ts = ""
                current = {
                    "hash": parts[0],
                    "author": parts[1],
                    "message": parts[3].strip(),
                    "timestamp": ts,
                    "files_changed": 0,
                    "insertions": 0,
                    "deletions": 0,
                }
            continue

        if not current or not line.strip():
            continue

        stat_parts = line.split("\t")
        if len(stat_parts) < 3:
            continue

        current["files_changed"] += 1
        try:
            current["insertions"] += int(stat_parts[0]) if stat_parts[0] != "-" else 0
            current["deletions"] += int(stat_parts[1]) if stat_parts[1] != "-" else 0
        except ValueError:
            pass

    if current:
        current["health_score"] = calculate_health(current)
        commits.append(current)

    return commits


def _process_commits_fast_log(repo: Repo, total_commits: int) -> list:
    logger.info("Using fast git log parser for %s commits", f"{total_commits:,}")
    started = time.perf_counter()
    pretty = f"%H{_LOG_FIELD_SEP}%an{_LOG_FIELD_SEP}%at{_LOG_FIELD_SEP}%s"
    output = repo.git.log(
        "--no-renames",
        f"--pretty=format:{pretty}",
        "--numstat",
    )
    commit_data = _parse_git_log_numstat(output)
    elapsed = time.perf_counter() - started
    logger.info(
        "Fast log parsed %s commits in %.1fs",
        f"{len(commit_data):,}",
        elapsed,
    )
    return commit_data, elapsed


def _process_all_commits(repo: Repo) -> tuple:
    try:
        total_commits = int(repo.git.rev_list("--count", "HEAD"))
    except GitCommandError as exc:
        raise RepoAnalysisError(f"Failed to read commit history: {exc}") from exc

    if total_commits > MAX_COMMITS_HARD_CAP:
        raise RepoAnalysisError(
            f"Repository has {total_commits:,} commits, which exceeds the "
            f"safety limit of {MAX_COMMITS_HARD_CAP:,}. "
            "Try a smaller fork or increase MAX_COMMITS_HARD_CAP in backend/.env."
        )

    if total_commits > FAST_LOG_THRESHOLD:
        commit_data, parse_elapsed = _process_commits_fast_log(repo, total_commits)
        if len(commit_data) != total_commits:
            logger.warning(
                "Fast parser count mismatch: expected %s, got %s",
                total_commits,
                len(commit_data),
            )
        return commit_data, total_commits, parse_elapsed

    logger.info("Analyzing %s commits (full history, detailed mode)...", f"{total_commits:,}")
    started = time.perf_counter()
    commit_data = []
    errors = 0

    for index, commit in enumerate(repo.iter_commits(), start=1):
        try:
            committed = commit.committed_datetime
            commit_info = {
                "hash": commit.hexsha,
                "author": str(commit.author),
                "message": (commit.message or "").strip(),
                "timestamp": committed.isoformat() if committed else "",
                **_commit_stats(commit),
            }
            commit_info["health_score"] = calculate_health(commit_info)
            commit_data.append(commit_info)
        except Exception as exc:
            errors += 1
            logger.warning("Skipped commit %s: %s", commit.hexsha, exc)
            if errors > 50:
                raise RepoAnalysisError(
                    f"Too many commit processing errors ({errors}). Aborting analysis."
                ) from exc

        if index % PROGRESS_LOG_EVERY == 0 or index == total_commits:
            elapsed = time.perf_counter() - started
            rate = index / elapsed if elapsed > 0 else 0
            logger.info(
                "Progress: %s / %s commits (%.1f commits/sec, %.1fs elapsed)",
                f"{index:,}",
                f"{total_commits:,}",
                rate,
                elapsed,
            )

    elapsed = time.perf_counter() - started
    logger.info(
        "Finished analyzing %s commits in %.1fs (%s skipped)",
        f"{len(commit_data):,}",
        elapsed,
        errors,
    )

    if len(commit_data) != total_commits:
        logger.warning(
            "Commit count mismatch: rev-list=%s, processed=%s",
            total_commits,
            len(commit_data),
        )

    return commit_data, total_commits, elapsed


def analyze_repo(repo_url: str) -> dict:
    repo_url = _validate_repo_url(repo_url)
    repo_name = _parse_repo_name(repo_url)
    repo_path = DATA_DIR / repo_name

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    repo = _ensure_full_clone(repo_url, repo_path)
    commit_data, total_commits, analysis_seconds = _process_all_commits(repo)

    graph = build_graph(commit_data)
    graph_meta = graph.get("meta", {})
    warnings = []

    node_count = len(graph.get("nodes", []))
    if graph_meta.get("truncated_for_display"):
        warnings.append(
            f"Knowledge graph shows the {graph_meta.get('commits_in_graph', 0)} most recent "
            f"commits for performance. All {len(commit_data):,} commits were analyzed for "
            "health scores and timeline."
        )
    if node_count >= GRAPH_NODE_WARN_THRESHOLD:
        warnings.append(
            f"Graph has {node_count:,} nodes — the browser view may be slow. "
            "Consider filtering by date range in a future release."
        )
    if total_commits >= 1000:
        warnings.append(
            f"Large repository ({total_commits:,} commits). "
            f"Analysis took {analysis_seconds:.1f}s."
        )

    ai_summary = ""
    if commit_data:
        try:
            ai_summary = generate_summary(commit_data[0])
        except AISummaryError as exc:
            ai_summary = f"AI summary unavailable: {exc}"
            logger.warning("AI summary failed: %s", exc)

    return {
        "repo": repo_name,
        "total_commits": total_commits,
        "commits_analyzed": len(commit_data),
        "commit_analysis": commit_data,
        "graph": graph,
        "ai_summary": ai_summary,
        "analysis_seconds": round(analysis_seconds, 2),
        "warnings": warnings,
    }
