"""
ManoKart — Offline LLM Engine (Ollama / Llama-3.2-1B)
=====================================================
Communicates with local Ollama service running on port 11434.
Generates empathetic, CBT-guided responses enriched with RAG context.
"""

import requests
import logging
from backend.rag_engine import query_rag

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:1b"

SYSTEM_PROMPT = """You are ManoKart AI Counselor, an empathetic, supportive, and active-listening CBT mental health assistant.
Your goal is to offer compassionate support, psychological coping strategies, and thoughtful reflections.

RULES:
1. Use the provided Clinical & Coping Context to guide your response.
2. Keep responses warm, helpful, and concise (2 to 3 short paragraphs).
3. Do NOT provide medical prescriptions or formal medical diagnoses.
4. Always encourage self-care and professional guidance when needed."""

def is_ollama_running() -> bool:
    """Check if Ollama service is responsive."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False

def generate_offline_counselor_response(user_query: str) -> dict:
    """
    Generate response using RAG + local Llama-3.2-1B model.
    Returns dict: {"response": str, "mode": "offline_rag_llm", "context_used": bool}
    """
    # 1. Retrieve RAG context from vector store
    rag_context = query_rag(user_query, top_k=2)
    has_context = bool(rag_context.strip())

    # 2. Build full prompt
    full_prompt = f"""{SYSTEM_PROMPT}

[RETRIEVED CLINICAL & COPING CONTEXT]
{rag_context if has_context else 'No specific matching context found.'}

[USER QUESTION / MESSAGE]
{user_query}

ManoKart Counselor Response:"""

    # 3. Request Ollama local service
    try:
        payload = {
            "model": MODEL_NAME,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_ctx": 2048
            }
        }
        res = requests.post(OLLAMA_URL, json=payload, timeout=25)
        if res.status_code == 200:
            text = res.json().get("response", "").strip()
            return {
                "response": text,
                "mode": "offline_rag_llm",
                "context_used": has_context,
                "model": MODEL_NAME
            }
        else:
            return {
                "response": "I'm having trouble processing your request locally right now.",
                "mode": "error"
            }
    except Exception as e:
        logger.error(f"Ollama generation error: {e}")
        return {
            "response": None,
            "mode": "offline_unavailable",
            "error": str(e)
        }
