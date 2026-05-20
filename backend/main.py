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


import json
from pathlib import Path
from analyzer.config import DATA_DIR
from analyzer.git_analyzer import _parse_repo_name

class SandboxRefactorRequest(BaseModel):
    repo_url: str
    filepath: str
    anti_pattern: str

@app.post("/sandbox/refactor")
def sandbox_refactor(body: SandboxRefactorRequest):
    try:
        repo_name = _parse_repo_name(body.repo_url)
        repo_path = DATA_DIR / repo_name
        clean_path = body.filepath.replace("\\", "/").lstrip("/")
        file_absolute_path = repo_path / clean_path
        
        file_content = ""
        if file_absolute_path.exists() and file_absolute_path.is_file():
            try:
                # Read up to 200 lines to fit LLM context efficiently
                with open(file_absolute_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    file_content = "".join(lines[:200])
            except Exception as e:
                logger.warning("Could not read file for sandbox: %s", e)
                
        # Call the LLM to generate dynamic refactoring code block and advisory
        prompt = (
            f"You are a Senior Software Architect AI. The user is exploring a refactoring blueprint in the Interactive Sandbox.\n"
            f"Target File: {body.filepath}\n"
            f"Anti-Pattern Category: {body.anti_pattern}\n"
        )
        if file_content:
            prompt += f"Here is a snippet of the actual file contents (up to 200 lines):\n```\n{file_content}\n```\n"
        else:
            prompt += f"No source file contents were read. Please simulate a realistic source code snippet matching the file extension of '{body.filepath}'.\n"
            
        prompt += (
            "\nTask:\n"
            "Generate a highly specific, customized refactoring blueprint. The output MUST be a JSON object with exactly three keys:\n"
            "1. 'advisory': string (explanation of the code anti-pattern in the file and how the refactored code fixes it)\n"
            "2. 'before_code': string (a code snippet demonstrating the anti-pattern, tailored to the file's language and path)\n"
            "3. 'after_code': string (the optimized, clean, refactored version of the code snippet)\n\n"
            "Ensure the output is valid JSON, do NOT wrap it in Markdown code blocks (like ```json), just output the raw JSON object."
        )
        
        messages = [
            {"role": "system", "content": "You are a professional software engineering analyzer that outputs ONLY raw valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        reply, model_used = call_llm(messages)
        
        # Clean reply if LLM output wraps in code block
        reply = reply.strip()
        if reply.startswith("```"):
            lines = reply.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            reply = "\n".join(lines).strip()
            
        try:
            parsed = json.loads(reply)
            before_val = parsed.get("before_code", "")
            if not isinstance(before_val, str):
                before_val = json.dumps(before_val, indent=2)
            after_val = parsed.get("after_code", "")
            if not isinstance(after_val, str):
                after_val = json.dumps(after_val, indent=2)
            return {
                "advisory": str(parsed.get("advisory", "")),
                "before_code": before_val,
                "after_code": after_val,
                "model": model_used
            }
        except Exception as json_exc:
            logger.warning("Failed to parse LLM response as JSON: %s. Response was: %s", json_exc, reply)
            return {
                "advisory": f"Advisory for {body.filepath} ({body.anti_pattern}): {reply[:300]}...",
                "before_code": f"# Original code in {body.filepath}",
                "after_code": f"# Refactored code in {body.filepath}",
                "model": model_used
            }
    except Exception as exc:
        logger.exception("Unexpected sandbox refactor error")
        raise HTTPException(status_code=500, detail=str(exc))


class CicdCheckRequest(BaseModel):
    repo_url: str
    filepath: str
    insertions: int
    deletions: int

@app.post("/cicd/check")
def cicd_check(body: CicdCheckRequest):
    try:
        repo_name = _parse_repo_name(body.repo_url)
        repo_path = DATA_DIR / repo_name
        clean_path = body.filepath.replace("\\", "/").lstrip("/")
        file_absolute_path = repo_path / clean_path
        base_lines = 100
        if file_absolute_path.exists() and file_absolute_path.is_file():
            try:
                with open(file_absolute_path, "r", encoding="utf-8") as f:
                    base_lines = len(f.readlines())
            except Exception:
                pass
                
        base_risk = min(95, max(35, int(35 + (base_lines / 10))))
        computed_risk = base_risk + (body.insertions / 5) - (body.deletions / 10)
        passed = computed_risk < 75
        
        prompt = (
            f"You are a Senior Software Architect AI. The user is checking a simulated PR change in the CI/CD Guard.\n"
            f"Target File: {body.filepath} (estimated current lines: {base_lines})\n"
            f"Simulated Changes: +{body.insertions} insertions, -{body.deletions} deletions.\n"
            f"Computed Risk Score: {computed_risk:.1f}/100 (Threshold for Pass: 75).\n"
            f"Status: {'PASS' if passed else 'FAIL'}.\n\n"
            f"Write a brief 2-3 sentence technical report from the Sentinel CI/CD Guard explaining why this change was "
            f"{'approved' if passed else 'blocked'} and what architectural concerns/off-sets apply."
        )
        
        messages = [
            {"role": "system", "content": "You are a professional CI/CD telemetry analysis bot. Keep your answers brief, expert-level, and to the point."},
            {"role": "user", "content": prompt}
        ]
        
        reply, model_used = call_llm(messages)
        
        return {
            "passed": passed,
            "risk_score": round(computed_risk, 1),
            "base_risk": base_risk,
            "report": reply,
            "model": model_used
        }
    except Exception as exc:
        logger.exception("Unexpected cicd check error")
        raise HTTPException(status_code=500, detail=str(exc))


class ForecastRequest(BaseModel):
    repo_url: str
    refactor_hotspots: bool
    add_tests: bool
    onboard_devs: int
    churn_velocity: int
    base_health: int

@app.post("/forecast/simulate")
def forecast_simulate(body: ForecastRequest):
    try:
        score = body.base_health
        if body.refactor_hotspots:
            score += 15
        if body.add_tests:
            score += 10
            
        onboarding_penalty = body.onboard_devs * 1.8
        churn_penalty = (body.churn_velocity - 1) * 4.5
        
        if body.add_tests:
            score -= onboarding_penalty * 0.3
        else:
            score -= onboarding_penalty
            
        score -= churn_penalty
        projected_score = min(100, max(10, round(score)))
        
        prompt = (
            f"You are a Senior Software Architect AI. The user is running a future health forecast simulator for their codebase.\n"
            f"Repository: {body.repo_url}\n"
            f"Baseline Health Score: {body.base_health}\n"
            f"Simulated Parameters:\n"
            f"- Refactor Critical Hotspots: {body.refactor_hotspots}\n"
            f"- Add Automated Unit Tests: {body.add_tests}\n"
            f"- Collaborator Onboarding: {body.onboard_devs} developers\n"
            f"- Commit Velocity: {body.churn_velocity}x speed\n\n"
            f"Projected Health Score: {projected_score}/100\n\n"
            f"Write a concise 2-3 sentence Technical Simulation Report summarizing the architectural prognosis under these conditions and outlining recommended preventatives."
        )
        
        messages = [
            {"role": "system", "content": "You are a professional software engineering forecast analyst. Keep your report crisp, specific, and actionable."},
            {"role": "user", "content": prompt}
        ]
        
        reply, model_used = call_llm(messages)
        
        return {
            "projected_score": projected_score,
            "report": reply,
            "model": model_used
        }
    except Exception as exc:
        logger.exception("Unexpected forecast simulation error")
        raise HTTPException(status_code=500, detail=str(exc))


