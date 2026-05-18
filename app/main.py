from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.services.job_runner import JobRunner
from app.storage.database import Database


@asynccontextmanager
async def lifespan(app: FastAPI):
    database = Database(settings.db_path)
    database.initialize()
    runner = JobRunner(database=database, settings=settings)
    app.state.database = database
    app.state.job_runner = runner
    yield


app = FastAPI(
    title="Repository Health Intelligence Backend",
    version="0.1.0",
    summary="Git ingestion, commit mining, hotspot scoring, ownership analytics, and health APIs.",
    description=(
        "Backend service for repository ingestion, commit traversal, static analysis, "
        "hotspot detection, ownership analytics, dependency graph extraction, and "
        "repository health scoring."
    ),
    lifespan=lifespan,
    openapi_tags=[
        {"name": "system", "description": "Service health and base discovery routes."},
        {"name": "repositories", "description": "Repository registration, sync, and executive summaries."},
        {"name": "analysis", "description": "Commit history, hotspots, dependencies, and health metrics."},
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
