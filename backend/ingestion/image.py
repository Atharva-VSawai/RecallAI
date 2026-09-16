import logging
import base64
import httpx
from groq import Groq
from core.config import settings

logger = logging.getLogger(__name__)

_VISION_MODEL_CANDIDATES = (
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
)


def _is_model_not_found_error(error: Exception) -> bool:
    message = str(error).lower()
    return "model_not_found" in message or ("model" in message and "does not exist" in message)


def _available_vision_model(client: Groq, configured_model: str) -> str:
    """Return the configured model, or an accessible vision model if it is unavailable."""
    try:
        available_ids = {
            model_id
            for model in client.models.list().data
            if (model_id := getattr(model, "id", None))
        }
    except Exception:
        logger.warning("[IMAGE OCR] Could not discover Groq models; retaining configured model")
        return configured_model

    # The configured model has already failed at this point, so prefer a
    # different accessible candidate before considering it again.
    for model_id in (*_VISION_MODEL_CANDIDATES, configured_model):
        if model_id in available_ids:
            if model_id != configured_model:
                logger.warning(
                    "[IMAGE OCR] Model '%s' is unavailable; using '%s' instead",
                    configured_model,
                    model_id,
                )
            return model_id

    return configured_model

def extract_text_from_image(file_bytes: bytes, filename: str, provider: str = "groq") -> str:
    """Extract image text using the selected provider's vision model."""
    base64_image = base64.b64encode(file_bytes).decode('utf-8')
    ext = filename.lower().split('.')[-1]
    mime_type = f"image/{ext}" if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp'] else "image/jpeg"
    prompt = "Extract all text from this image. Include decisions, discussions, notes, and organizational information. Return only the extracted text, preserving structure and formatting where possible."
    
    try:
        logger.info(f"[IMAGE OCR] Processing '{filename}' ({len(file_bytes)} bytes)")
        
        if provider.lower() == "ollama":
            response = httpx.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                json={
                    "model": settings.ollama_vision_model,
                    "messages": [{"role": "user", "content": prompt, "images": [base64_image]}],
                    "stream": False,
                },
                timeout=180.0,
            )
            response.raise_for_status()
            text = response.json().get("message", {}).get("content", "")
            if not text:
                raise ValueError("Ollama returned no OCR text")
        else:
            client = Groq(api_key=settings.groq_api_key)
            request = {
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}},
                    ],
                }],
                "temperature": 0,
                "max_completion_tokens": 4096,
            }
            model = settings.groq_vision_model
            try:
                completion = client.chat.completions.create(model=model, **request)
            except Exception as first_error:
                if not _is_model_not_found_error(first_error):
                    raise
                model = _available_vision_model(client, model)
                if model == settings.groq_vision_model:
                    raise
                completion = client.chat.completions.create(model=model, **request)
            text = completion.choices[0].message.content or ""
            if not text:
                raise ValueError("Groq returned no OCR text")
        logger.info(f"[IMAGE OCR] ✓ Extracted {len(text)} characters")
        return text
        
    except Exception as e:
        logger.error(f"[IMAGE OCR] Failed: {e}")
        raise ValueError(f"Image OCR failed: {str(e)}")
