from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.analyzers.file_analyzer import FileAnalyzer
from app.core.config import Settings
from app.services.git_client import GitClient
from app.services.repository_analyzer import RepositoryAnalyzer
from app.storage.database import Database


class JobRunner:
    def __init__(self, database: Database, settings: Settings) -> None:
        self.database = database
        self.settings = settings
        self.git_client = GitClient(settings)
        self.file_analyzer = FileAnalyzer()
        self.repository_analyzer = RepositoryAnalyzer(database, settings, self.git_client, self.file_analyzer)
        self._tasks: dict[str, asyncio.Task] = {}

    async def schedule_repository_sync(
        self,
        repo_id: str,
        branch: str | None = None,
        max_commits: int | None = None,
        force_reanalyze: bool = False,
    ) -> dict:
        if repo_id in self._tasks and not self._tasks[repo_id].done():
            raise RuntimeError("A sync job is already running for this repository.")
        repo = self.database.get_repository(repo_id)
        if repo is None:
            raise KeyError(repo_id)
        payload = {
            "branch": branch,
            "max_commits": max_commits,
            "force_reanalyze": force_reanalyze,
        }
        job = self.database.create_job(repo_id, "repository_sync", payload)
        task = asyncio.create_task(
            self._run_repository_sync(
                job_id=job["id"],
                repo_id=repo_id,
                branch=branch,
                max_commits=max_commits,
                force_reanalyze=force_reanalyze,
            )
        )
        self._tasks[repo_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(repo_id, None))
        return job

    async def _run_repository_sync(
        self,
        job_id: str,
        repo_id: str,
        branch: str | None,
        max_commits: int | None,
        force_reanalyze: bool,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        self.database.update_job(
            job_id,
            status="running",
            progress=0.01,
            message="Starting repository sync",
            started_at=now,
            error=None,
        )
        self.database.update_repository(repo_id, status="syncing")

        repo = self.database.get_repository(repo_id)
        if repo is None:
            self.database.update_job(
                job_id,
                status="failed",
                progress=1.0,
                finished_at=datetime.now(UTC).isoformat(),
                error="Repository not found.",
            )
            return

        def progress_callback(progress: float, message: str) -> None:
            self.database.update_job(job_id, progress=round(progress, 4), message=message)

        try:
            await asyncio.to_thread(
                self.repository_analyzer.analyze_repository,
                repo,
                progress_callback,
                branch,
                max_commits,
                force_reanalyze,
            )
        except Exception as exc:  # noqa: BLE001
            self.database.update_job(
                job_id,
                status="failed",
                progress=1.0,
                message="Repository analysis failed",
                finished_at=datetime.now(UTC).isoformat(),
                error=str(exc),
            )
            self.database.update_repository(repo_id, status="failed")
            return

        self.database.update_job(
            job_id,
            status="completed",
            progress=1.0,
            message="Repository analysis completed",
            finished_at=datetime.now(UTC).isoformat(),
            error=None,
        )

