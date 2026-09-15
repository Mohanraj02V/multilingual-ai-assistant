from app.services.llm.base import LLMProvider
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def get_llm_provider() -> LLMProvider:
    """Factory function — returns the configured LLM provider.
    
    To add a new provider:
    1. Import it here
    2. Add a case to the if/elif chain below
    """
    provider = settings.llm_provider.lower()

    if provider == "ollama":
        from app.services.llm.ollama import OllamaProvider
        return OllamaProvider()

    # Future providers — uncomment and implement when ready:
    # elif provider == "openai":
    #     from app.services.llm.openai import OpenAIProvider
    #     return OpenAIProvider()
    #
    # elif provider == "gemini":
    #     from app.services.llm.gemini import GeminiProvider
    #     return GeminiProvider()
    #
    # elif provider == "groq":
    #     from app.services.llm.groq import GroqProvider
    #     return GroqProvider()

    else:
        logger.warning(f"Unknown LLM provider '{provider}', falling back to Ollama")
        from app.services.llm.ollama import OllamaProvider
        return OllamaProvider()
