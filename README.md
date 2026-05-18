# Repository Health Intelligence Backend

Production-oriented hackathon backend for repository ingestion, commit mining, hotspot analysis, ownership tracking, dependency graph extraction, and repository health scoring.

## What is implemented

- FastAPI service for repository registration, sync, status, commits, hotspots, dependency edges, and health summary
- Git ingestion using bare mirrors and commit traversal through the Git CLI
- Commit-level mining of:
  - changed files
  - churn
  - complexity deltas
  - ownership entropy
  - hotspot exposure
  - heuristic risk scoring
- Multi-language static analysis for:
  - Python
  - JavaScript / TypeScript
  - Java
  - Go
  - C / C++
- Current dependency graph extraction from repository HEAD
- SQLite-backed persistence for repositories, jobs, commits, commit files, file snapshots, hotspots, dependency edges, and metric timelines
- Direct CLI for local demo analysis

## Project layout

```text
repository-health-intelligence/
  app/
    api/
    analyzers/
    core/
    services/
    storage/
  data/
    clones/
  run_analysis.py
  requirements.txt
```

## Quick start

```bash
cd "/Users/uditsinghi/Documents/New project/repository-health-intelligence"
python3 -m uvicorn app.main:app --reload
```

API base: `http://127.0.0.1:8000`

## Useful endpoints

- `POST /v1/repositories`
- `POST /v1/repositories/{repo_id}/sync`
- `GET /v1/repositories`
- `GET /v1/repositories/{repo_id}`
- `GET /v1/repositories/{repo_id}/summary`
- `GET /v1/repositories/{repo_id}/health`
- `GET /v1/repositories/{repo_id}/commits`
- `GET /v1/repositories/{repo_id}/commits/{sha}`
- `GET /v1/repositories/{repo_id}/hotspots`
- `GET /v1/repositories/{repo_id}/dependencies`
- `GET /v1/repositories/{repo_id}/metrics/{metric_key}`

## Example: register a repo

```bash
curl -X POST http://127.0.0.1:8000/v1/repositories \
  -H "content-type: application/json" \
  -d '{
    "repo_url": "/absolute/path/to/repo",
    "display_name": "demo-repo",
    "max_commits": 300
  }'
```

## Example: run analysis without the API

```bash
python3 run_analysis.py "/absolute/path/to/repo" --max-commits 200
```

## Current architecture notes

- Persistence is intentionally lightweight tonight: SQLite now, schema designed so PostgreSQL migration is straightforward.
- Git operations are deterministic and content-driven, with analysis derived from commit replay rather than any LLM dependency.
- Dependency resolution is strongest for Python and JS/TS relative imports; Java/Go/C-family handling is intentionally heuristic in this MVP.
- The background worker uses in-process asyncio tasks for speed of implementation. A production next step would be to swap this for Redis/Kafka + Temporal or Celery.

## Recommended next steps after the hackathon

1. Replace SQLite with PostgreSQL and move large analysis artifacts to object storage.
2. Add parser-backed semantic analyzers such as Tree-sitter or language-native compilers.
3. Add true incremental sync by storing lineage checkpoints instead of full-window recompute.
4. Add graph persistence in Neo4j or Memgraph for architecture-drift queries.
5. Add pre-merge risk scoring with a trained tabular model.
