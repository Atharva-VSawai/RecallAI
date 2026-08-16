import httpx
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from core.config import settings
import logging
from application.services.observability_service import breakers, store

logger = logging.getLogger(__name__)


def _token_count(response) -> int:
    usage = getattr(response, "usage_metadata", None) or getattr(response, "response_metadata", {}).get("token_usage", {})
    if isinstance(usage, dict):
        return int(usage.get("total_tokens") or usage.get("total_token_count") or usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0))
    return max(1, len(str(getattr(response, "content", ""))) // 4)


class ObservedLLM:
    """Transparent Runnable proxy that records tokens and provider failures."""
    def __init__(self, delegate, provider: str):
        self._delegate = delegate
        self.provider = provider

    def invoke(self, *args, **kwargs):
        response = breakers[self.provider].call(lambda: self._delegate.invoke(*args, **kwargs))
        store.record_usage("llm", self.provider, _token_count(response))
        return response

    async def ainvoke(self, *args, **kwargs):
        if not breakers[self.provider].allow():
            raise RuntimeError(f"Provider circuit is open: {self.provider}")
        try:
            response = await self._delegate.ainvoke(*args, **kwargs)
            breakers[self.provider].success()
        except Exception:
            breakers[self.provider].failure()
            store.metric("provider_failure", provider=self.provider)
            raise
        store.record_usage("llm", self.provider, _token_count(response))
        return response

    def bind_tools(self, *args, **kwargs):
        return ObservedLLM(self._delegate.bind_tools(*args, **kwargs), self.provider)

    def __getattr__(self, name):
        return getattr(self._delegate, name)

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
    provider = (provider or "").strip().lower()
    if provider not in {"groq", "ollama"}:
        raise ValueError("Unsupported LLM provider")
    
    if provider == "ollama":
        if is_ollama_reachable():
            logger.info(f"[LLM] Instantiating Local ChatOllama (model: {settings.ollama_model})")
            kwargs = {
                "model": settings.ollama_model,
                "temperature": temperature
            }
            if is_json:
                kwargs["format"] = "json"
                
            return ObservedLLM(ChatOllama(**kwargs), "ollama")
        else:
            logger.warning("[LLM] Ollama was requested but is not running. Falling back to Groq.")
            provider = "groq" # Fallthrough to Groq
            
    if provider == "groq":
        logger.info("[LLM] Instantiating Cloud ChatGroq (model: llama-3.3-70b-versatile)")
        return ObservedLLM(ChatGroq(
            api_key=settings.groq_api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=temperature
        ), "groq")
