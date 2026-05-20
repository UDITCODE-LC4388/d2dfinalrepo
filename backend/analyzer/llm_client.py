import os
import logging
import requests
from dotenv import load_dotenv
from analyzer.config import BACKEND_DIR

# Ensure environment variables are loaded
load_dotenv(BACKEND_DIR / ".env")

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

TIMEOUT_SECONDS = 8

def generate_local_fallback_answer(messages, context_items):
    """
    Formulate a smart, deterministic fallback answer in case all LLM APIs fail.
    Utilizes the retrieved context items to supply correct information.
    """
    user_query = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_query = msg.get("content", "").lower()
            break

    # Construct clean answer using context items
    if context_items:
        best_context = context_items[0]
        title = best_context.get("title", "Documentation")
        content = best_context.get("content", "")
        
        reply = (
            f"I retrieved information regarding '{title}' from our local Vector DB, but I was unable to connect "
            f"to the remote AI completion engines (DeepSeek/Groq).\n\n"
            f"Here is the official documentation for your query:\n\n{content}\n\n"
            f"Please check your internet connection or verify your API keys in the `.env` file to restore full AI capability."
        )
    else:
        reply = (
            "I'm sorry, I'm currently offline and could not retrieve relevant documentation from my vector database. "
            "Additionally, both DeepSeek and Groq API keys were unreachable or failed. Please check your network connection "
            "and configure the backend `.env` variables correctly to activate Sentinel Copilot."
        )
    return reply

def call_llm(messages: list, context_items: list = None) -> tuple[str, str]:
    """
    Generate a completion response using a multi-provider strategy:
    1. Try DeepSeek (Primary)
    2. Fallback to Groq (Secondary)
    3. Fallback to Local context-guided generation (Resilient Sandbox)

    Returns:
        tuple[str, str]: (reply_text, model_identifier)
    """
    # 1. Attempt DeepSeek Call
    if DEEPSEEK_API_KEY:
        try:
            logger.info("Attempting AI completion via DeepSeek (%s)...", DEEPSEEK_MODEL)
            response = requests.post(
                DEEPSEEK_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 800,
                },
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()
            reply = payload["choices"][0]["message"]["content"].strip()
            logger.info("DeepSeek AI call successful.")
            return reply, "DeepSeek-V3"
        except Exception as exc:
            logger.warning("DeepSeek API call failed or timed out: %s. Falling back to Groq.", exc)
    else:
        logger.info("DeepSeek API Key is not set. Skipping to Groq.")

    # 2. Attempt Groq Fallback
    if GROQ_API_KEY:
        models_to_try = [GROQ_MODEL, "llama-3.1-8b-instant", "groq/compound-mini", "groq/compound"]
        import time
        for model in models_to_try:
            for attempt in range(3):
                try:
                    logger.info("Attempting AI completion via Groq (%s) [attempt %d/3]...", model, attempt + 1)
                    response = requests.post(
                        GROQ_URL,
                        headers={
                            "Authorization": f"Bearer {GROQ_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": messages,
                            "temperature": 0.3,
                            "max_tokens": 800,
                        },
                        timeout=TIMEOUT_SECONDS,
                    )
                    if response.status_code == 429:
                        wait_sec = (attempt + 1) * 1.5
                        logger.warning("Groq model %s returned 429. Waiting %.1fs to retry...", model, wait_sec)
                        time.sleep(wait_sec)
                        continue
                    response.raise_for_status()
                    payload = response.json()
                    reply = payload["choices"][0]["message"]["content"].strip()
                    logger.info("Groq AI call successful with model %s.", model)
                    return reply, f"Groq-{model}"
                except Exception as exc:
                    logger.warning("Groq API call failed for model %s: %s.", model, exc)
                    break
    else:
        logger.info("Groq API Key is not set. Skipping to Local Fallback.")

    # 3. Local Smart Fallback
    logger.warning("All LLM APIs failed. Triggering offline local sandbox response.")
    local_reply = generate_local_fallback_answer(messages, context_items or [])
    return local_reply, "Offline-Retriever"
