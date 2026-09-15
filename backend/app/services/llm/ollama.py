import httpx
import json
import logging
from typing import List, Dict, Any, Optional
import asyncio

from app.services.llm.base import LLMProvider
from app.config import settings

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama LLM provider — calls the local Ollama API."""

    def __init__(self):
        self._base_url = settings.ollama_base_url
        self._model = settings.ollama_model
        self._timeout = settings.ollama_timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Send a chat completion request to Ollama."""
        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
            },
        }

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        f"{self._base_url}/api/chat",
                        json=payload,
                    )
                    
                    if response.status_code == 404:
                        logger.error(f"Model '{self._model}' not found in Ollama.")
                        raise httpx.HTTPStatusError(
                            f"Model '{self._model}' not found. Run 'ollama pull {self._model}'", 
                            request=response.request, 
                            response=response
                        )
                        
                    response.raise_for_status()
                    data = response.json()
                    return data["message"]["content"].strip()
                    
            except httpx.HTTPStatusError as e:
                # 404s (model missing) or 400s are terminal, do not retry
                if e.response.status_code in (404, 400):
                    raise
                if attempt == 0:
                    logger.warning(f"Transient HTTP error from Ollama ({e.response.status_code}), retrying...")
                    await asyncio.sleep(1)
                else:
                    raise
            except httpx.RequestError as e:
                if attempt == 0:
                    logger.warning(f"Connection error to Ollama ({e}), retrying...")
                    await asyncio.sleep(1)
                else:
                    raise

    async def is_available(self) -> bool:
        """Ping Ollama to verify it's running."""
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{self._base_url}/api/tags")
                    return response.status_code == 200
            except httpx.RequestError as e:
                if attempt == 0:
                    await asyncio.sleep(0.5)
                else:
                    logger.error(f"Ollama availability check failed: Unable to connect to {self._base_url}")
                    return False
            except Exception as e:
                logger.warning(f"Ollama availability check failed: {e}")
                return False

    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for a given text string using Ollama."""
        payload = {
            "model": settings.ollama_embedding_model,
            "prompt": text,
            "keep_alive": "30m"
        }
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        f"{self._base_url}/api/embeddings",
                        json=payload,
                    )
                    
                    if response.status_code == 404:
                        logger.error(f"Embedding model '{settings.ollama_embedding_model}' not found in Ollama.")
                        raise httpx.HTTPStatusError(
                            f"Model '{settings.ollama_embedding_model}' not found. Run 'ollama pull {settings.ollama_embedding_model}'", 
                            request=response.request, 
                            response=response
                        )
                        
                    response.raise_for_status()
                    data = response.json()
                    return data["embedding"]
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (404, 400):
                    raise
                if attempt == 0:
                    logger.warning(f"Transient HTTP error for embeddings ({e.response.status_code}), retrying...")
                    await asyncio.sleep(1)
                else:
                    raise
            except httpx.RequestError as e:
                if attempt == 0:
                    logger.warning(f"Connection error for embeddings ({e}), retrying...")
                    await asyncio.sleep(1)
                else:
                    raise
        return []
        return False
