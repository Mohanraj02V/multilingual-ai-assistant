import logging
import re
from typing import Tuple, Optional
from langdetect import detect as ld_detect, LangDetectException

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
    """Detects the language of a text string using a 3-tier cascade:
    1. Unicode Script Range Check
    2. langdetect (Latin-script)
    3. LLM Fallback (Code-mixed/Transliterated)
    """

    def __init__(self, llm_provider: LLMProvider):
        self._llm = llm_provider

    def _detect_by_script(self, text: str) -> Optional[str]:
        """Tier 1: Check for specific Unicode script ranges."""
        scripts = {
            "ta": r"[\u0B80-\u0BFF]",  # Tamil
            "hi": r"[\u0900-\u097F]",  # Devanagari (Hindi, Marathi)
            "te": r"[\u0C00-\u0C7F]",  # Telugu
            "ml": r"[\u0D00-\u0D7F]",  # Malayalam
            "kn": r"[\u0C80-\u0CFF]",  # Kannada
            "bn": r"[\u0980-\u09FF]",  # Bengali
        }
        
        text_len = len(text.replace(" ", ""))
        if text_len == 0:
            return None
            
        for lang_code, pattern in scripts.items():
            matches = len(re.findall(pattern, text))
            if matches / text_len > 0.2:
                return lang_code
        return None

    def _detect_by_langdetect(self, text: str) -> Optional[str]:
        """Tier 2: Use langdetect for High Resource Latin script languages."""
        if len(text) < 15:
            return None
            
        try:
            lang = ld_detect(text)
            # Only trust langdetect for high-resource Latin languages
            if lang in ["en", "es", "fr", "de", "pt", "it"]:
                return lang
        except LangDetectException:
            pass
            
        return None

    async def detect(self, text: str) -> Tuple[str, str]:
        """Detect the language of text."""
        # Tier 1: Script check (Fast, accurate for Indic scripts)
        script_lang = self._detect_by_script(text)
        if script_lang and script_lang in SUPPORTED_LANGUAGES:
            logger.info(f"Language detection Tier 1 (Script): {script_lang}")
            return script_lang, SUPPORTED_LANGUAGES[script_lang]
            
        # Tier 2: langdetect (Fast, accurate for Latin script)
        ld_lang = self._detect_by_langdetect(text)
        if ld_lang and ld_lang in SUPPORTED_LANGUAGES:
            logger.info(f"Language detection Tier 2 (langdetect): {ld_lang}")
            return ld_lang, SUPPORTED_LANGUAGES[ld_lang]

        # Tier 3: LLM Fallback (handles code-mixed, Romanized Indic, short text)
        logger.info("Language detection Tier 3 (LLM fallback) triggered")
        
        lang_list = ", ".join(
            f"{name} ({code})" for code, name in SUPPORTED_LANGUAGES.items()
        )
        
        system_prompt = (
            "You are a language detection expert. "
            "Respond with ONLY the ISO 639-1 two-letter language code (e.g. 'en', 'ta', 'hi'). "
            "Do not include any explanation, punctuation, or other text. "
            f"Supported languages: {lang_list}"
        )
        
        user_message = (
            f"Detect the language of this text. It might be written in Latin script but actually "
            f"be a phonetic transcription of another language (e.g. Tamil or Hindi transliterated).\n\n"
            f"Text: '{text}'"
        )

        try:
            result = await self._llm.generate(system_prompt, user_message)
            code = result.strip().lower()[:5]

            code = "".join(c for c in code if c.isalpha())[:2]

            if code in SUPPORTED_LANGUAGES:
                return code, SUPPORTED_LANGUAGES[code]

            logger.warning(f"Unrecognized language code '{code}', defaulting to English")
            return "en", "English"

        except Exception as e:
            logger.exception("Language detection failed:")
            return "en", "English"

    def get_language_name(self, code: str) -> str:
        """Get human-readable name for a language code."""
        return SUPPORTED_LANGUAGES.get(code, "English")
