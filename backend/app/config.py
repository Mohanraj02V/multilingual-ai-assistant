from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    environment: str = "development"
    admin_api_key: str = ""

    # LLM Provider
    llm_provider: str = "ollama"

    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    
    @field_validator("ollama_base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith("http"):
            raise ValueError("ollama_base_url must start with http:// or https://")
        return v.rstrip("/")
    ollama_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_timeout: int = 60

    # Retrieval settings
    max_context_documents: int = 5
    retrieval_min_score: float = 0.55

    # Input limits
    max_message_length: int = 2000
    max_conversation_turns: int = 10

    # CORS
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # Knowledge base path
    knowledge_base_path: str = "data/knowledge.json"

    # STT settings (beam_size=2 interim default; tune via STT_BEAM_SIZE env var)
    stt_beam_size: int = 2

    # LLM generation limit (tokens) — prevents runaway generation
    llm_num_predict: int = 400

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
