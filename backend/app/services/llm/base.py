from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class LLMProvider(ABC):
    """Abstract base class for all LLM providers.
    
    To add a new provider (e.g., OpenAI, Gemini, Groq):
    1. Create a new file in this directory (e.g., openai.py)
    2. Subclass LLMProvider
    3. Implement all abstract methods
    4. Register the provider in factory.py
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Generate a response from the LLM.
        
        Args:
            system_prompt: The system instruction for the LLM.
            user_message: The current user message.
            conversation_history: Optional list of prior turns [{role, content}].
            
        Returns:
            The generated text response.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check whether the provider is reachable and ready.
        
        Returns:
            True if the provider can accept requests.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name for this provider."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model identifier being used."""
        ...
