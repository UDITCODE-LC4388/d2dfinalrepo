from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
import shutil

from app.core.config import Settings


@dataclass(slots=True)
class CommitChange:
    path: str
    old_path: str | None
    change_type: str
    additions: int
    deletions: int


class GitCommandError(RuntimeError):
    pass


class GitClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _run(
        self,
        *args: str,
        git_dir: Path | None = None,
        check: bool = True,
        binary: bool = False,
    ) -> str | bytes:
        command = ["git"]
        if git_dir is not None:
            command.extend(["--git-dir", str(git_dir)])
        command.extend(args)
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if check and completed.returncode != 0:
            raise GitCommandError(completed.stderr.decode("utf-8", errors="ignore").strip())
        if binary:
            return completed.stdout
        return completed.stdout.decode("utf-8", errors="ignore")

    def prepare_repository(self, repo_url: str, clone_path: Path) -> None:
        clone_path.parent.mkdir(parents=True, exist_ok=True)
        source = repo_url
        local_path = Path(repo_url).expanduser()
        if local_path.exists():
            source = str(local_path.resolve())
        if clone_path.exists() and (clone_path / "HEAD").exists():
            self._run("fetch", "--all", "--tags", "--prune", git_dir=clone_path)
            return
        if clone_path.exists():
            shutil.rmtree(clone_path)
        self._run("clone", "--bare", source, str(clone_path))

    def infer_default_branch(self, clone_path: Path, requested_branch: str | None = None) -> str:
        if requested_branch:
            branch_exists = self._run(
                "show-ref",
                "--verify",
                f"refs/heads/{requested_branch}",
                git_dir=clone_path,
                check=False,
            )
            if branch_exists:
                return requested_branch
        head = self._run("symbolic-ref", "--short", "HEAD", git_dir=clone_path).strip()
        return head.removeprefix("refs/heads/")

    def list_commits(self, clone_path: Path, branch: str, max_commits: int) -> list[str]:
        output = self._run(
            "rev-list",
            "--reverse",
            "--topo-order",
            f"--max-count={max_commits}",
            branch,
            git_dir=clone_path,
        )
        return [line.strip() for line in output.splitlines() if line.strip()]

    def read_commit_metadata(self, clone_path: Path, sha: str, commit_index: int) -> dict[str, str | int]:
        output = self._run(
            "show",
            "-s",
            "--format=%H%x1f%an%x1f%ae%x1f%aI%x1f%P%x1f%s",
            sha,
            git_dir=clone_path,
        ).strip()
        parts = output.split("\x1f")
        parents = parts[4].split() if len(parts) > 4 and parts[4] else []
        return {
            "sha": parts[0],
            "author_name": parts[1],
            "author_email": parts[2],
            "authored_at": parts[3],
            "parent_count": len(parents),
            "message": parts[5] if len(parts) > 5 else "",
            "commit_index": commit_index,
        }

    def read_commit_changes(self, clone_path: Path, sha: str) -> list[CommitChange]:
        status_output = self._run(
            "diff-tree",
            "--root",
            "--no-commit-id",
            "-r",
            "-M",
            "--name-status",
            sha,
            git_dir=clone_path,
        )
        numstat_output = self._run(
            "diff-tree",
            "--root",
            "--no-commit-id",
            "-r",
            "-M",
            "--numstat",
            sha,
            git_dir=clone_path,
        )
        stats_by_path: dict[str, tuple[int, int]] = {}
        stats_by_pair: dict[tuple[str, str], tuple[int, int]] = {}

        for line in numstat_output.splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            additions = int(parts[0]) if parts[0].isdigit() else 0
            deletions = int(parts[1]) if parts[1].isdigit() else 0
            if len(parts) >= 4:
                stats_by_pair[(parts[2], parts[3])] = (additions, deletions)
                stats_by_path[parts[3]] = (additions, deletions)
            else:
                stats_by_path[parts[2]] = (additions, deletions)

        changes: list[CommitChange] = []
        for line in status_output.splitlines():
            parts = line.split("\t")
            if not parts:
                continue
            change_code = parts[0]
            change_type = change_code[0]
            old_path: str | None = None
            path: str
            if change_type in {"R", "C"} and len(parts) >= 3:
                old_path = parts[1]
                path = parts[2]
                additions, deletions = stats_by_pair.get(
                    (old_path, path),
                    stats_by_path.get(path, (0, 0)),
                )
            else:
                path = parts[1]
                additions, deletions = stats_by_path.get(path, (0, 0))
            changes.append(
                CommitChange(
                    path=path,
                    old_path=old_path,
                    change_type=change_type,
                    additions=additions,
                    deletions=deletions,
                )
            )
        return changes

    def file_exists(self, clone_path: Path, rev: str, path: str) -> bool:
        result = self._run("cat-file", "-e", f"{rev}:{path}", git_dir=clone_path, check=False)
        return result == ""

    def read_file_text(self, clone_path: Path, rev: str, path: str, max_bytes: int) -> str | None:
        size_output = self._run("cat-file", "-s", f"{rev}:{path}", git_dir=clone_path, check=False)
        if not size_output.strip().isdigit():
            return None
        if int(size_output.strip()) > max_bytes:
            return None
        raw = self._run("show", f"{rev}:{path}", git_dir=clone_path, binary=True)
        if not isinstance(raw, bytes) or b"\x00" in raw:
            return None
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="ignore")
