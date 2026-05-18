import requests

from analyzer.config import GROQ_API_KEY
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
REQUEST_TIMEOUT_SECONDS = 30


class AISummaryError(Exception):
    pass


def generate_summary(commit: dict) -> str:
    if not GROQ_API_KEY:
        raise AISummaryError("GROQ_API_KEY is not set in backend/.env")

    prompt = f"""Explain this repository health change.

Files changed: {commit['files_changed']}
Insertions: {commit['insertions']}
Deletions: {commit['deletions']}
Health score: {commit['health_score']}

Give a concise engineering explanation in 2-4 sentences."""

    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]
    except requests.Timeout as exc:
        raise AISummaryError("Groq API request timed out") from exc
    except requests.HTTPError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("error", {}).get("message", "")
        except Exception:
            pass
        raise AISummaryError(detail or str(exc)) from exc
    except (KeyError, IndexError, ValueError) as exc:
        raise AISummaryError("Unexpected Groq API response format") from exc
    except requests.RequestException as exc:
        raise AISummaryError(f"Groq API request failed: {exc}") from exc
