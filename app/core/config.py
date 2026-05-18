from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Settings:
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2])
    data_dir: Path = field(init=False)
    clone_dir: Path = field(init=False)
    db_path: Path = field(init=False)
    max_commits_per_sync: int = 500
    max_file_bytes: int = 512_000
    max_changed_files_per_commit: int = 250
    vendor_roots: tuple[str, ...] = (
        "node_modules",
        "vendor",
        ".git",
        "dist",
        "build",
        "coverage",
        ".next",
        ".venv",
        "venv",
        "__pycache__",
        "target",
    )
    text_extensions: tuple[str, ...] = (
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".go",
        ".c",
        ".cc",
        ".cpp",
        ".cxx",
        ".h",
        ".hpp",
        ".hh",
        ".mjs",
        ".mts",
        ".cts",
        ".json",
        ".yml",
        ".yaml",
        ".toml",
        ".md",
        ".sql",
    )

    def __post_init__(self) -> None:
        self.data_dir = self.project_root / "data"
        self.clone_dir = self.data_dir / "clones"
        self.db_path = self.data_dir / "repository_health.db"
        self.clone_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()

