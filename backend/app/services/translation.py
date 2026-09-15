import logging
from typing import AsyncGenerator

from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class TranslationService:
    """Translation service using the LLM.
    
    This can later be replaced with a dedicated translation API
    (e.g., DeepL, Google Translate, Azure Translator) without
    changing the interface.
    """

    def __init__(self, llm_provider: LLMProvider):
        self._llm = llm_provider

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        source_name: str = "",
        target_name: str = "",
    ) -> str:
        """Translate text from source to target language.
        
        Args:
            text: The text to translate.
            source_language: ISO 639-1 source language code.
            target_language: ISO 639-1 target language code.
            source_name: Human-readable source language name.
            target_name: Human-readable target language name.
            
        Returns:
            The translated text.
        """
        # No translation needed
        if source_language == target_language:
            return text

        src_label = source_name or source_language
        tgt_label = target_name or target_language

        system_prompt = (
            f"You are a professional translator. "
            f"Translate the following text from {src_label} to {tgt_label}. "
            f"Return ONLY the translated text with no explanations, notes, or extra formatting. "
            f"Preserve the original meaning precisely."
        )

        try:
            translated = await self._llm.generate(system_prompt, text)
            return translated.strip()
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text  # Fall back to original text on error

    async def to_english(
        self,
        text: str,
        source_language: str,
        source_name: str = "",
    ) -> str:
        """Convenience method: translate any language to English."""
        return await self.translate(
            text=text,
            source_language=source_language,
            target_language="en",
            source_name=source_name,
            target_name="English",
        )

    async def from_english(
        self,
        text: str,
        target_language: str,
        target_name: str = "",
    ) -> str:
        """Convenience method: translate English to any language."""
        return await self.translate(
            text=text,
            source_language="en",
            target_language=target_language,
            source_name="English",
            target_name=target_name,
        )

    async def stream_from_english(
        self,
        text: str,
        target_language: str,
        target_name: str = "",
    ) -> AsyncGenerator[str, None]:
        """Stream translation from English to target language token by token.

        Uses the LLM's stream_generate so the translated tokens arrive at the
        frontend progressively rather than waiting for the full translation.
        """
        tgt_label = target_name or target_language
        system_prompt = (
            f"You are a professional translator. "
            f"Translate the following text from English to {tgt_label}. "
            f"Return ONLY the translated text with no explanations, notes, or extra formatting. "
            f"Preserve the original meaning precisely."
        )
        async for token in self._llm.stream_generate(system_prompt, text):
            yield token
