from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.analyzers.file_analyzer import FileAnalyzer
from app.core.config import settings
from app.services.git_client import GitClient
from app.services.repository_analyzer import RepositoryAnalyzer
from app.storage.database import Database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repository ingestion + health analysis against a local or remote Git repository."
    )
    parser.add_argument("repo_url", help="Local filesystem path or remote Git URL")
    parser.add_argument("--name", dest="display_name", default=None, help="Optional display name")
    parser.add_argument("--branch", default=None, help="Branch to analyze")
    parser.add_argument("--max-commits", type=int, default=200, help="Maximum commit depth to traverse")
    parser.add_argument(
        "--force-reanalyze",
        action="store_true",
        help="Clear existing analysis tables before running.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_url = str(Path(args.repo_url).expanduser().resolve()) if Path(args.repo_url).exists() else args.repo_url
    database = Database(settings.db_path)
    database.initialize()
    repository = database.find_repository_by_url(repo_url)
    if repository is None:
        repository = database.create_repository(
            display_name=args.display_name or Path(repo_url).name or "repository",
            repo_url=repo_url,
            clone_path=str(settings.clone_dir / "pending"),
            default_branch=args.branch,
            max_commits=args.max_commits,
        )
        repository = database.update_repository(
            repository["id"],
            clone_path=str(settings.clone_dir / repository["id"]),
        )
    else:
        repository = database.update_repository(
            repository["id"],
            max_commits=args.max_commits,
        )

    analyzer = RepositoryAnalyzer(
        database=database,
        settings=settings,
        git_client=GitClient(settings),
        file_analyzer=FileAnalyzer(),
    )
    result = analyzer.analyze_repository(
        repo=repository,
        progress_callback=lambda progress, message: print(f"[{progress:>5.1%}] {message}"),
        branch=args.branch,
        max_commits=args.max_commits,
        force_reanalyze=args.force_reanalyze,
    )
    metrics = database.get_repo_metrics(repository["id"])
    summary = {
        "result": result,
        "health_index": metrics.get("health_index", {}).get("value"),
        "code_health": metrics.get("code_health", {}).get("value"),
        "team_health": metrics.get("team_health", {}).get("value"),
        "architecture_health": metrics.get("architecture_health", {}).get("value"),
        "temporal_health": metrics.get("temporal_health", {}).get("value"),
        "top_risks": metrics.get("health_index", {}).get("payload", {}).get("top_risks", []),
        "languages": metrics.get("health_index", {}).get("payload", {}).get("languages", {}),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

