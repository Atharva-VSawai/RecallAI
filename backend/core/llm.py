from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from core.config import settings
import logging

logger = logging.getLogger(__name__)

def get_llm(provider: str = "groq", temperature: float = 0, is_json: bool = False):
    """
    Factory function to get the requested LLM provider dynamically.
    :param provider: "groq" or "ollama"
    :param temperature: LLM temperature setting
    """
    provider = provider.lower()
    
    if provider == "ollama":
        logger.info(f"[LLM] Instantiating Local ChatOllama (model: {settings.ollama_model})")
        kwargs = {
            "model": settings.ollama_model,
            "temperature": temperature
        }
        if is_json:
            kwargs["format"] = "json"
            
        return ChatOllama(**kwargs)
    else:
        logger.info("[LLM] Instantiating Cloud ChatGroq (model: llama-3.3-70b-versatile)")
        return ChatGroq(
            api_key=settings.groq_api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=temperature
        )
