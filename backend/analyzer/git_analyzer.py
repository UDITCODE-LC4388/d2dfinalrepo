import logging
import shutil
from urllib.parse import urlparse

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from analyzer.ai_summary import AISummaryError, generate_summary
from analyzer.config import COMMIT_LIMIT, DATA_DIR
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


def analyze_repo(repo_url: str) -> dict:
    repo_url = _validate_repo_url(repo_url)
    repo_name = _parse_repo_name(repo_url)
    repo_path = DATA_DIR / repo_name

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not repo_path.exists():
        last_error = None
        for attempt in range(2):
            try:
                Repo.clone_from(
                    repo_url,
                    repo_path,
                    depth=COMMIT_LIMIT,
                    single_branch=True,
                )
                last_error = None
                break
            except GitCommandError as exc:
                last_error = exc
                if repo_path.exists():
                    shutil.rmtree(repo_path, ignore_errors=True)
        if last_error is not None:
            raise RepoAnalysisError(f"Failed to clone repository: {last_error}") from last_error

    try:
        repo = Repo(repo_path)
    except InvalidGitRepositoryError as exc:
        raise RepoAnalysisError(f"Invalid git repository at {repo_path}") from exc

    try:
        total_commits = int(repo.git.rev_list("--count", "HEAD"))
    except GitCommandError as exc:
        raise RepoAnalysisError(f"Failed to read commit history: {exc}") from exc

    commit_data = []
    for commit in repo.iter_commits(max_count=COMMIT_LIMIT):
        commit_info = {
            "hash": commit.hexsha,
            "author": str(commit.author),
            "message": (commit.message or "").strip(),
            **_commit_stats(commit),
        }
        commit_info["health_score"] = calculate_health(commit_info)
        commit_data.append(commit_info)

    graph = build_graph(commit_data)

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
    }
