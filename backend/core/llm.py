import httpx
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from core.config import settings
import logging

logger = logging.getLogger(__name__)

def is_ollama_reachable() -> bool:
    """Quickly check if the local Ollama instance is actually running."""
    try:
        # A fast 0.5s timeout ping to check if the server is up
        res = httpx.get(settings.ollama_base_url.rstrip("/") + "/", timeout=0.5)
        return res.status_code == 200
    except Exception:
        return False

def get_llm(provider: str = "groq", temperature: float = 0, is_json: bool = False):
    """
    Factory function to get the requested LLM provider dynamically.
    :param provider: "groq" or "ollama"
    :param temperature: LLM temperature setting
    """
    provider = provider.lower()
    
    if provider == "ollama":
        if is_ollama_reachable():
            logger.info(f"[LLM] Instantiating Local ChatOllama (model: {settings.ollama_model})")
            kwargs = {
                "model": settings.ollama_model,
                "temperature": temperature
            }
            if is_json:
                kwargs["format"] = "json"
                
            return ChatOllama(**kwargs)
        else:
            logger.warning("[LLM] Ollama was requested but is not running. Falling back to Groq.")
            provider = "groq" # Fallthrough to Groq
            
    if provider == "groq":
        logger.info("[LLM] Instantiating Cloud ChatGroq (model: llama-3.3-70b-versatile)")
        return ChatGroq(
            api_key=settings.groq_api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=temperature
        )
