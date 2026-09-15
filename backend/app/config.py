from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # LLM Provider
    llm_provider: str = "ollama"

    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout: int = 60

    # Retrieval settings
    max_context_documents: int = 5
    retrieval_min_score: float = 0.1

    # Input limits
    max_message_length: int = 2000
    max_conversation_turns: int = 10

    # CORS
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # Knowledge base path
    knowledge_base_path: str = "data/knowledge.json"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
