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


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    chat_history: list[ChatMessage] = Field(default_factory=list)


from analyzer.vector_db import vector_db
from analyzer.llm_client import call_llm


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


@app.post("/chat")
def chat(body: ChatRequest):
    try:
        query_text = body.message.strip()
        
        # 1. Query Vector DB to get top 2 matching documents
        matches = vector_db.query(query_text, top_k=2)
        
        # Extract matched documents with reasonable relevance score
        context_items = []
        context_blocks = []
        for doc, score in matches:
            if score > 0.05:  # Filter noise, keep only relevant documents
                context_items.append(doc)
                context_blocks.append(f"Source Document: {doc['title']}\nContent: {doc['content']}")
        
        # 2. Build RAG-enabled system prompt
        system_prompt = (
            "You are Sentinel Copilot, a senior software architect AI assistant built directly into the "
            "\"Repository Health Intelligence\" (Sentinel Prime) dashboard.\n"
            "Your goal is to interact with users, explain dashboard elements (like Health Score, Bus Factor, "
            "Hotspots, Architecture Stability, Collaboration Graph), and answer software engineering questions.\n\n"
            "Use the following retrieved platform knowledge from our Vector DB to accurately answer the user's query. "
            "Ground your explanations in these articles where applicable.\n"
        )
        
        if context_blocks:
            system_prompt += "\nRETRIEVED PLATFORM KNOWLEDGE:\n" + "\n---\n".join(context_blocks) + "\n\n"
            
        system_prompt += (
            "Formatting & Tone Guidelines:\n"
            "- Provide precise, expert-level architectural or general coding explanations.\n"
            "- Keep your tone professional, friendly, helpful, and concise.\n"
            "- Feel free to use light bullets or structured paragraphs for readability. Avoid complex raw HTML.\n"
            "- If the question is a simple greeting or general banter, respond politely and explain what Sentinel Prime is.\n"
        )
        
        # 3. Construct messages payload
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history (limit to last 6 messages to keep context efficient)
        for h in body.chat_history[-6:]:
            messages.append({"role": h.role, "content": h.content})
            
        # Add current user message
        messages.append({"role": "user", "content": query_text})
        
        # 4. Generate response using multi-provider client
        reply, model_used = call_llm(messages, context_items)
        
        return {
            "answer": reply,
            "sources": [doc["title"] for doc in context_items],
            "model_used": model_used
        }
    except Exception as exc:
        logger.exception("Unexpected error in /chat endpoint")
        raise HTTPException(status_code=500, detail="Internal server error in architectural assistant.") from exc

