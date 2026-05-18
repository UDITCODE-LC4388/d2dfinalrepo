from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from app.storage.schema import SCHEMA_SQL


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterable[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)

    def create_repository(
        self,
        display_name: str,
        repo_url: str,
        clone_path: str,
        default_branch: str | None,
        max_commits: int,
    ) -> dict[str, Any]:
        repo_id = str(uuid.uuid4())
        now = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO repositories (
                    id, display_name, repo_url, clone_path, default_branch, status,
                    max_commits, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    repo_id,
                    display_name,
                    repo_url,
                    clone_path,
                    default_branch,
                    "queued",
                    max_commits,
                    now,
                    now,
                ),
            )
        return self.get_repository(repo_id)

    def list_repositories(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM repositories ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_repository(self, repo_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM repositories WHERE id = ?", (repo_id,)
            ).fetchone()
        return dict(row) if row else None

    def find_repository_by_url(self, repo_url: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM repositories WHERE repo_url = ?", (repo_url,)
            ).fetchone()
        return dict(row) if row else None

    def update_repository(self, repo_id: str, **fields: Any) -> dict[str, Any]:
        if not fields:
            repository = self.get_repository(repo_id)
            if repository is None:
                raise KeyError(repo_id)
            return repository
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values())
        values.extend([utc_now(), repo_id])
        with self.connect() as connection:
            connection.execute(
                f"UPDATE repositories SET {assignments}, updated_at = ? WHERE id = ?",
                values,
            )
        repository = self.get_repository(repo_id)
        if repository is None:
            raise KeyError(repo_id)
        return repository

    def create_job(
        self,
        repo_id: str,
        job_type: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        now = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO analysis_jobs (
                    id, repo_id, job_type, status, progress, message,
                    payload_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    repo_id,
                    job_type,
                    "queued",
                    0.0,
                    "Queued for analysis",
                    json.dumps(payload or {}),
                    now,
                ),
            )
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM analysis_jobs WHERE id = ?", (job_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_latest_job_for_repo(self, repo_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM analysis_jobs
                WHERE repo_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (repo_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_job(self, job_id: str, **fields: Any) -> dict[str, Any]:
        if not fields:
            job = self.get_job(job_id)
            if job is None:
                raise KeyError(job_id)
            return job
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values())
        values.append(job_id)
        with self.connect() as connection:
            connection.execute(
                f"UPDATE analysis_jobs SET {assignments} WHERE id = ?",
                values,
            )
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(job_id)
        return job

    def clear_analysis(self, repo_id: str) -> None:
        with self.connect() as connection:
            for table in (
                "metric_timeline",
                "repo_metrics",
                "hotspots",
                "dependency_edges",
                "file_snapshots",
                "commit_files",
                "commits",
            ):
                connection.execute(f"DELETE FROM {table} WHERE repo_id = ?", (repo_id,))

    def replace_commits(
        self,
        repo_id: str,
        commits: list[dict[str, Any]],
        commit_files: list[dict[str, Any]],
        metric_timeline: list[dict[str, Any]],
    ) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO commits (
                    repo_id, sha, commit_index, author_name, author_email, authored_at,
                    message, parent_count, files_changed, additions, deletions, risk_score,
                    hotspot_score, complexity_delta, ownership_entropy, primary_language
                )
                VALUES (
                    :repo_id, :sha, :commit_index, :author_name, :author_email, :authored_at,
                    :message, :parent_count, :files_changed, :additions, :deletions, :risk_score,
                    :hotspot_score, :complexity_delta, :ownership_entropy, :primary_language
                )
                """,
                commits,
            )
            connection.executemany(
                """
                INSERT OR REPLACE INTO commit_files (
                    repo_id, commit_sha, path, old_path, change_type, language, additions, deletions,
                    complexity_before, complexity_after, symbols_before, symbols_after,
                    import_count_before, import_count_after
                )
                VALUES (
                    :repo_id, :commit_sha, :path, :old_path, :change_type, :language, :additions, :deletions,
                    :complexity_before, :complexity_after, :symbols_before, :symbols_after,
                    :import_count_before, :import_count_after
                )
                """,
                commit_files,
            )
            connection.executemany(
                """
                INSERT OR REPLACE INTO metric_timeline (
                    repo_id, commit_sha, commit_index, metric_key, value, measured_at
                )
                VALUES (
                    :repo_id, :commit_sha, :commit_index, :metric_key, :value, :measured_at
                )
                """,
                metric_timeline,
            )

    def replace_file_snapshots(self, repo_id: str, snapshots: list[dict[str, Any]]) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM file_snapshots WHERE repo_id = ?", (repo_id,))
            connection.executemany(
                """
                INSERT INTO file_snapshots (
                    repo_id, path, language, complexity, symbol_count, import_count,
                    line_count, total_churn, touch_count, contributor_count, ownership_entropy,
                    hotspot_score, dependencies_json, contributors_json, last_commit_sha,
                    last_author_email, last_modified_at, is_deleted
                )
                VALUES (
                    :repo_id, :path, :language, :complexity, :symbol_count, :import_count,
                    :line_count, :total_churn, :touch_count, :contributor_count, :ownership_entropy,
                    :hotspot_score, :dependencies_json, :contributors_json, :last_commit_sha,
                    :last_author_email, :last_modified_at, :is_deleted
                )
                """,
                snapshots,
            )

    def replace_dependency_edges(self, repo_id: str, edges: list[dict[str, Any]]) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM dependency_edges WHERE repo_id = ?", (repo_id,))
            if edges:
                connection.executemany(
                    """
                    INSERT INTO dependency_edges (
                        repo_id, source_path, target_path, edge_type, strength, last_seen_commit_sha
                    )
                    VALUES (
                        :repo_id, :source_path, :target_path, :edge_type, :strength, :last_seen_commit_sha
                    )
                    """,
                    edges,
                )

    def replace_hotspots(self, repo_id: str, hotspots: list[dict[str, Any]]) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM hotspots WHERE repo_id = ?", (repo_id,))
            if hotspots:
                connection.executemany(
                    """
                    INSERT INTO hotspots (
                        repo_id, path, language, churn, complexity, contributors,
                        ownership_entropy, hotspot_score, last_commit_sha
                    )
                    VALUES (
                        :repo_id, :path, :language, :churn, :complexity, :contributors,
                        :ownership_entropy, :hotspot_score, :last_commit_sha
                    )
                    """,
                    hotspots,
                )

    def replace_repo_metrics(self, repo_id: str, metrics: dict[str, Any]) -> None:
        now = utc_now()
        with self.connect() as connection:
            connection.execute("DELETE FROM repo_metrics WHERE repo_id = ?", (repo_id,))
            connection.executemany(
                """
                INSERT INTO repo_metrics (repo_id, metric_key, value, measured_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        repo_id,
                        metric_key,
                        float(metric_value["value"]),
                        now,
                        json.dumps(metric_value.get("payload", {})),
                    )
                    for metric_key, metric_value in metrics.items()
                ],
            )

    def list_commits(self, repo_id: str, limit: int, offset: int) -> tuple[int, list[dict[str, Any]]]:
        with self.connect() as connection:
            total = connection.execute(
                "SELECT COUNT(*) AS count FROM commits WHERE repo_id = ?",
                (repo_id,),
            ).fetchone()["count"]
            rows = connection.execute(
                """
                SELECT * FROM commits
                WHERE repo_id = ?
                ORDER BY commit_index DESC
                LIMIT ? OFFSET ?
                """,
                (repo_id, limit, offset),
            ).fetchall()
        return total, [dict(row) for row in rows]

    def get_commit(self, repo_id: str, sha: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM commits WHERE repo_id = ? AND sha = ?",
                (repo_id, sha),
            ).fetchone()
        return dict(row) if row else None

    def list_commit_files(self, repo_id: str, sha: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM commit_files
                WHERE repo_id = ? AND commit_sha = ?
                ORDER BY additions + deletions DESC, path ASC
                """,
                (repo_id, sha),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_hotspots(self, repo_id: str, limit: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM hotspots
                WHERE repo_id = ?
                ORDER BY hotspot_score DESC, churn DESC
                LIMIT ?
                """,
                (repo_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_metric_timeline(self, repo_id: str, metric_key: str, limit: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM metric_timeline
                WHERE repo_id = ? AND metric_key = ?
                ORDER BY commit_index DESC
                LIMIT ?
                """,
                (repo_id, metric_key, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_dependency_edges(self, repo_id: str, limit: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM dependency_edges
                WHERE repo_id = ?
                ORDER BY strength DESC, source_path ASC
                LIMIT ?
                """,
                (repo_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_riskiest_commits(self, repo_id: str, limit: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM commits
                WHERE repo_id = ?
                ORDER BY risk_score DESC, hotspot_score DESC, commit_index DESC
                LIMIT ?
                """,
                (repo_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_top_contributors(self, repo_id: str, limit: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    author_name,
                    author_email,
                    COUNT(*) AS commit_count,
                    SUM(additions + deletions) AS total_churn,
                    AVG(risk_score) AS average_commit_risk
                FROM commits
                WHERE repo_id = ?
                GROUP BY author_name, author_email
                ORDER BY total_churn DESC, commit_count DESC, average_commit_risk DESC
                LIMIT ?
                """,
                (repo_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_repo_metrics(self, repo_id: str) -> dict[str, dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM repo_metrics WHERE repo_id = ?",
                (repo_id,),
            ).fetchall()
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            result[row["metric_key"]] = {
                "value": row["value"],
                "measured_at": row["measured_at"],
                "payload": json.loads(row["payload_json"] or "{}"),
            }
        return result
