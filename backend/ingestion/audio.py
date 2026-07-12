import logging
import tempfile
from pathlib import Path
from groq import Groq
from core.config import settings

logger = logging.getLogger(__name__)

def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    """Transcribe audio/video file to text using Groq Whisper API."""
    client = Groq(api_key=settings.groq_api_key)
    
    # Save to temp file (Groq API requires file path)
    suffix = Path(filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    
    try:
        logger.info(f"[AUDIO] Transcribing '{filename}' ({len(file_bytes)} bytes)")
        
        with open(tmp_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(filename, audio_file.read()),
                model="whisper-large-v3",
                response_format="text"
            )
        
        text = transcription if isinstance(transcription, str) else transcription.text
        logger.info(f"[AUDIO] ✓ Transcribed {len(text)} characters")
        return text
        
    finally:
        Path(tmp_path).unlink(missing_ok=True)
