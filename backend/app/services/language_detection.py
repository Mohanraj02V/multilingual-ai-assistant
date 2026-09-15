import logging
from typing import Tuple

from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)

# Map of language codes to human-readable names
SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "te": "Telugu",
    "ml": "Malayalam",
    "kn": "Kannada",
    "bn": "Bengali",
    "mr": "Marathi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "zh": "Chinese",
    "ar": "Arabic",
    "pt": "Portuguese",
    "ru": "Russian",
    "ko": "Korean",
    "it": "Italian",
}


class LanguageDetectionService:
    """Detects the language of a text string using the LLM.
    
    This can later be replaced with a dedicated language detection library
    (e.g., langdetect, fasttext, or a cloud API) without changing the interface.
    """

    def __init__(self, llm_provider: LLMProvider):
        self._llm = llm_provider

    async def detect(self, text: str) -> Tuple[str, str]:
        """Detect the language of text.
        
        Returns:
            Tuple of (language_code, language_name), e.g. ("ta", "Tamil")
        """
        # Build list of supported languages for the prompt
        lang_list = ", ".join(
            f"{name} ({code})" for code, name in SUPPORTED_LANGUAGES.items()
        )

        system_prompt = (
            "You are a language detection expert. "
            "Respond with ONLY the ISO 639-1 two-letter language code (e.g. 'en', 'ta', 'hi'). "
            "Do not include any explanation, punctuation, or other text. "
            f"Supported languages: {lang_list}"
        )

        user_message = f"Detect the language of this text: {text}"

        try:
            result = await self._llm.generate(system_prompt, user_message)
            code = result.strip().lower()[:5]  # Take first 5 chars max

            # Clean up any extra characters
            code = "".join(c for c in code if c.isalpha())[:2]

            if code in SUPPORTED_LANGUAGES:
                return code, SUPPORTED_LANGUAGES[code]

            # Fallback: if unrecognized code, default to English
            logger.warning(f"Unrecognized language code '{code}', defaulting to English")
            return "en", "English"

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "en", "English"

    def get_language_name(self, code: str) -> str:
        """Get human-readable name for a language code."""
        return SUPPORTED_LANGUAGES.get(code, "English")
