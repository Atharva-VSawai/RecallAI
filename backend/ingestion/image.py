import logging
import base64
from groq import Groq
from core.config import settings

logger = logging.getLogger(__name__)

def extract_text_from_image(file_bytes: bytes, filename: str) -> str:
    """Extract text from image using Groq Vision API (OCR)."""
    client = Groq(api_key=settings.groq_api_key)
    
    # Convert image to base64
    base64_image = base64.b64encode(file_bytes).decode('utf-8')
    
    # Determine image type from filename
    ext = filename.lower().split('.')[-1]
    mime_type = f"image/{ext}" if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp'] else "image/jpeg"
    
    try:
        logger.info(f"[IMAGE OCR] Processing '{filename}' ({len(file_bytes)} bytes)")
        
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Extract all text from this image. Include any decisions, discussions, notes, or organizational information. Return only the extracted text, preserving structure and formatting where possible."
                        }
                    ]
                }
            ],
            temperature=0,
            max_tokens=4096
        )
        
        text = completion.choices[0].message.content
        logger.info(f"[IMAGE OCR] ✓ Extracted {len(text)} characters")
        return text
        
    except Exception as e:
        logger.error(f"[IMAGE OCR] Failed: {e}")
        raise ValueError(f"Image OCR failed: {str(e)}")
