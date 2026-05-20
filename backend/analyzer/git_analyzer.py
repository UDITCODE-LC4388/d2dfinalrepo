import logging
import os
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


def _analyze_languages(repo_path) -> list:
    extension_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JSX",
        ".ts": "TypeScript",
        ".tsx": "TSX",
        ".html": "HTML",
        ".css": "CSS",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".cpp": "C++",
        ".cc": "C++",
        ".c": "C",
        ".h": "C/C++ Header",
        ".sh": "Shell",
        ".md": "Markdown",
        ".json": "JSON",
        ".yml": "YAML",
        ".yaml": "YAML",
        ".sql": "SQL",
        ".rb": "Ruby",
        ".php": "PHP",
    }
    
    stats = {}
    total_bytes = 0
    
    ignore_dirs = {".git", "node_modules", "venv", "env", "dist", "build", ".next", ".sass-cache", "__pycache__"}
    
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if os.path.islink(file_path):
                    continue
                size = os.path.getsize(file_path)
                _, ext = os.path.splitext(file.lower())
                lang = extension_map.get(ext)
                if lang:
                    if lang not in stats:
                        stats[lang] = {"count": 0, "bytes": 0}
                    stats[lang]["count"] += 1
                    stats[lang]["bytes"] += size
                    total_bytes += size
            except Exception:
                pass
                
    languages = []
    if total_bytes > 0:
        for name, data in stats.items():
            pct = round((data["bytes"] / total_bytes) * 100, 1)
            if pct > 0:
                languages.append({
                    "language": name,
                    "file_count": data["count"],
                    "bytes": data["bytes"],
                    "percentage": pct
                })
        languages.sort(key=lambda x: x["percentage"], reverse=True)
        
    return languages


def _calculate_file_churn(repo) -> list:
    file_churn_map = {}
    try:
        # Run git log --numstat directly to extract complete historical changes
        output = repo.git.log("--no-renames", "--numstat", "--pretty=format:")
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            try:
                ins = int(parts[0]) if parts[0] != "-" else 0
                dels = int(parts[1]) if parts[1] != "-" else 0
                filepath = parts[2].strip()
                if filepath:
                    # Ignore vendor/dependencies
                    if not any(x in filepath for x in ("node_modules", "vendor", "dist", "env", "venv", ".git", "__pycache__")):
                        if filepath not in file_churn_map:
                            file_churn_map[filepath] = {"churn": 0, "insertions": 0, "deletions": 0}
                        file_churn_map[filepath]["churn"] += 1
                        file_churn_map[filepath]["insertions"] += ins
                        file_churn_map[filepath]["deletions"] += dels
            except ValueError:
                pass
    except Exception as exc:
        logger.warning("Could not calculate file churn: %s", exc)
        
    hotspots = []
    for filepath, stats in file_churn_map.items():
        total_delta = stats["insertions"] + stats["deletions"]
        # risk heuristic: frequency of modification and total lines impacted, normalized to avoid capping at 100 for all top hotspots
        risk_score = int(45 + (stats["churn"] * 0.5) + (total_delta // 150))
        hotspots.append({
            "filepath": filepath,
            "churn": stats["churn"],
            "insertions": stats["insertions"],
            "deletions": stats["deletions"],
            "risk_score": min(98, max(30, risk_score))
        })
    # sort by risk_score descending
    hotspots.sort(key=lambda x: x["risk_score"], reverse=True)
    return hotspots[:10]


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

    languages = _analyze_languages(repo_path)
    hotspots = _calculate_file_churn(repo)
    dangerous_commit = _find_most_dangerous_commit(commit_data, repo)

    return {
        "repo": repo_name,
        "total_commits": total_commits,
        "commits_analyzed": len(commit_data),
        "commit_analysis": commit_data,
        "graph": graph,
        "ai_summary": ai_summary,
        "analysis_seconds": round(analysis_seconds, 2),
        "warnings": warnings,
        "languages": languages,
        "hotspots": hotspots,
        "dangerous_commit": dangerous_commit,
    }

def _find_most_dangerous_commit(commit_data: list, repo) -> dict:
    if not commit_data:
        return None
    
    highest_danger_score = -1.0
    dangerous_commit = None
    
    for i in range(len(commit_data)):
        commit = commit_data[i]
        
        files_changed = commit.get("files_changed", 0)
        insertions = commit.get("insertions", 0)
        deletions = commit.get("deletions", 0)
        message = (commit.get("message") or "").lower()
        
        danger_score = (files_changed * 3.5) + (insertions * 0.05) + (deletions * 0.02)
        
        keywords = ["remove", "bypass", "disable", "force", "hack", "refactor", "hotfix", "critical", "broken", "undo"]
        for kw in keywords:
            if kw in message:
                danger_score += 15.0
                
        health_drop = 0
        if i + 1 < len(commit_data):
            prev_health = commit_data[i + 1].get("health_score", 100)
            curr_health = commit.get("health_score", 100)
            health_drop = max(0, prev_health - curr_health)
            danger_score += health_drop * 4.0
            
        commit["danger_score"] = danger_score
        commit["health_drop"] = health_drop
        
        if danger_score > highest_danger_score:
            highest_danger_score = danger_score
            dangerous_commit = commit

    if dangerous_commit:
        affected_files = []
        try:
            files_str = repo.git.show("--name-only", "--pretty=format:", dangerous_commit["hash"])
            affected_files = [f.strip() for f in files_str.split("\n") if f.strip()]
        except Exception:
            affected_files = ["main.py"]
            
        from analyzer.ai_summary import generate_danger_explanation
        ai_exp = generate_danger_explanation(dangerous_commit)
        
        return {
            "hash": dangerous_commit["hash"],
            "author": dangerous_commit.get("author", "Unknown Author"),
            "date": dangerous_commit.get("timestamp", "").split("T")[0],
            "health_drop": dangerous_commit.get("health_drop", 15),
            "affected_files": affected_files[:10],
            "ai_explanation": ai_exp
        }
    return None
