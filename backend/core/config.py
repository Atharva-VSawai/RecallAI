from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    groq_api_key: str = ""
    neo4j_uri: str = ""
    neo4j_username: str = ""
    neo4j_password: str = ""
    slack_bot_token: str = ""
    cohere_api_key: str = ""
    chroma_tenant: str = ""
    chroma_api_key: str = ""
    chroma_database: str = "notes"
    ollama_model: str = "llama3.1:latest"
    ollama_base_url: str = "http://localhost:11434"
    # llama3.1 is text-only. Image OCR requires a separate vision model.
    ollama_vision_model: str = "llama3.2-vision"
    groq_vision_model: str = "qwen/qwen3.6-27b"
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    # Backwards-compatible name for projects that still expose the legacy anon key.
    supabase_anon_key: str = ""
    supabase_jwt_audience: str = "authenticated"
    supabase_jwt_issuer: str = ""
    cors_origins: str = "http://localhost:3000"
    max_upload_size_bytes: int = 25 * 1024 * 1024
    log_level: str = "INFO"

    class Config:
        env_file = Path(__file__).resolve().parent.parent / ".env"

settings = Settings()
