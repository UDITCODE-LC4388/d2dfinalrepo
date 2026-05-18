SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS repositories (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    repo_url TEXT NOT NULL,
    clone_path TEXT NOT NULL,
    default_branch TEXT,
    status TEXT NOT NULL,
    max_commits INTEGER NOT NULL,
    last_synced_at TEXT,
    last_analyzed_commit TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_jobs (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL,
    progress REAL NOT NULL DEFAULT 0,
    message TEXT,
    payload_json TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_jobs_repo_created
ON analysis_jobs (repo_id, created_at DESC);

CREATE TABLE IF NOT EXISTS commits (
    repo_id TEXT NOT NULL,
    sha TEXT NOT NULL,
    commit_index INTEGER NOT NULL,
    author_name TEXT NOT NULL,
    author_email TEXT NOT NULL,
    authored_at TEXT NOT NULL,
    message TEXT NOT NULL,
    parent_count INTEGER NOT NULL,
    files_changed INTEGER NOT NULL,
    additions INTEGER NOT NULL,
    deletions INTEGER NOT NULL,
    risk_score REAL NOT NULL,
    hotspot_score REAL NOT NULL,
    complexity_delta REAL NOT NULL,
    ownership_entropy REAL NOT NULL,
    primary_language TEXT NOT NULL,
    PRIMARY KEY (repo_id, sha),
    FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_commits_repo_index
ON commits (repo_id, commit_index DESC);

CREATE TABLE IF NOT EXISTS commit_files (
    repo_id TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    path TEXT NOT NULL,
    old_path TEXT,
    change_type TEXT NOT NULL,
    language TEXT NOT NULL,
    additions INTEGER NOT NULL,
    deletions INTEGER NOT NULL,
    complexity_before REAL NOT NULL,
    complexity_after REAL NOT NULL,
    symbols_before INTEGER NOT NULL,
    symbols_after INTEGER NOT NULL,
    import_count_before INTEGER NOT NULL,
    import_count_after INTEGER NOT NULL,
    PRIMARY KEY (repo_id, commit_sha, path),
    FOREIGN KEY (repo_id, commit_sha) REFERENCES commits(repo_id, sha) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_commit_files_repo_path
ON commit_files (repo_id, path);

CREATE TABLE IF NOT EXISTS file_snapshots (
    repo_id TEXT NOT NULL,
    path TEXT NOT NULL,
    language TEXT NOT NULL,
    complexity REAL NOT NULL,
    symbol_count INTEGER NOT NULL,
    import_count INTEGER NOT NULL,
    line_count INTEGER NOT NULL,
    total_churn INTEGER NOT NULL,
    touch_count INTEGER NOT NULL,
    contributor_count INTEGER NOT NULL,
    ownership_entropy REAL NOT NULL,
    hotspot_score REAL NOT NULL,
    dependencies_json TEXT NOT NULL,
    contributors_json TEXT NOT NULL,
    last_commit_sha TEXT,
    last_author_email TEXT,
    last_modified_at TEXT,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (repo_id, path),
    FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_file_snapshots_repo_hotspot
ON file_snapshots (repo_id, hotspot_score DESC);

CREATE TABLE IF NOT EXISTS dependency_edges (
    repo_id TEXT NOT NULL,
    source_path TEXT NOT NULL,
    target_path TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    strength REAL NOT NULL,
    last_seen_commit_sha TEXT,
    PRIMARY KEY (repo_id, source_path, target_path, edge_type),
    FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hotspots (
    repo_id TEXT NOT NULL,
    path TEXT NOT NULL,
    language TEXT NOT NULL,
    churn INTEGER NOT NULL,
    complexity REAL NOT NULL,
    contributors INTEGER NOT NULL,
    ownership_entropy REAL NOT NULL,
    hotspot_score REAL NOT NULL,
    last_commit_sha TEXT,
    PRIMARY KEY (repo_id, path),
    FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS repo_metrics (
    repo_id TEXT NOT NULL,
    metric_key TEXT NOT NULL,
    value REAL NOT NULL,
    measured_at TEXT NOT NULL,
    payload_json TEXT,
    PRIMARY KEY (repo_id, metric_key),
    FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metric_timeline (
    repo_id TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    commit_index INTEGER NOT NULL,
    metric_key TEXT NOT NULL,
    value REAL NOT NULL,
    measured_at TEXT NOT NULL,
    PRIMARY KEY (repo_id, commit_sha, metric_key),
    FOREIGN KEY (repo_id, commit_sha) REFERENCES commits(repo_id, sha) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_metric_timeline_repo_key
ON metric_timeline (repo_id, metric_key, commit_index DESC);
"""

