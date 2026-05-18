import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"

# Graph shown in UI — full history is still analyzed for scores/timeline
GRAPH_DISPLAY_MAX_COMMITS = int(os.getenv("GRAPH_DISPLAY_MAX_COMMITS", "500"))

# Use single `git log --numstat` pass above this commit count (much faster)
FAST_LOG_THRESHOLD = int(os.getenv("FAST_LOG_THRESHOLD", "250"))

# Log progress every N commits on large repos
PROGRESS_LOG_EVERY = int(os.getenv("PROGRESS_LOG_EVERY", "100"))

# Warn in API response when graph is truncated for the frontend
GRAPH_NODE_WARN_THRESHOLD = int(os.getenv("GRAPH_NODE_WARN_THRESHOLD", "800"))

# Refuse analysis above this count to protect server memory (override via env)
MAX_COMMITS_HARD_CAP = int(os.getenv("MAX_COMMITS_HARD_CAP", "50000"))

load_dotenv(BACKEND_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
