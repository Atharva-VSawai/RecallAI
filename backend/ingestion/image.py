import logging
import base64
import httpx
from groq import Groq
from core.config import settings

logger = logging.getLogger(__name__)

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
            completion = client.chat.completions.create(
                model=settings.groq_vision_model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}},
                    ],
                }],
                temperature=0,
                max_completion_tokens=4096,
            )
            text = completion.choices[0].message.content or ""
            if not text:
                raise ValueError("Groq returned no OCR text")
        logger.info(f"[IMAGE OCR] ✓ Extracted {len(text)} characters")
        return text
        
    except Exception as e:
        logger.error(f"[IMAGE OCR] Failed: {e}")
        raise ValueError(f"Image OCR failed: {str(e)}")
