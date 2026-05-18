import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from analyzer.git_analyzer import RepoAnalysisError, analyze_repo
from analyzer.response_mapper import map_to_frontend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Repo Health Intelligence API",
    description="Analyze GitHub repositories for commit health, graphs, and AI summaries.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="Git repository URL")


@app.get("/")
def home():
    return {"message": "Repo Health Intelligence API Running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/analyze")
def analyze(body: AnalyzeRequest):
    try:
        raw = analyze_repo(body.url)
        return map_to_frontend(raw)
    except RepoAnalysisError as exc:
        logger.warning("Analysis failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected analysis error")
        raise HTTPException(status_code=500, detail="Internal server error during analysis") from exc
