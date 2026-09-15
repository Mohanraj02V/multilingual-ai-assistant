import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.models.schemas import (
    ChatRequest, ChatResponse,
    DetectLanguageRequest, DetectLanguageResponse,
    TranslateRequest, TranslateResponse,
)
from app.services.llm.factory import get_llm_provider
from app.services.conversation import ConversationService
from app.services.language_detection import LanguageDetectionService, SUPPORTED_LANGUAGES
from app.services.translation import TranslationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint — processes text/voice input and returns an answer."""
    try:
        llm = get_llm_provider()
        service = ConversationService(llm)
        response = await service.process(request)
        return response
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="The AI service is currently unavailable. Please try again."
        )


@router.post("/language/detect", response_model=DetectLanguageResponse)
async def detect_language(request: DetectLanguageRequest):
    """Detect the language of a piece of text."""
    try:
        llm = get_llm_provider()
        detector = LanguageDetectionService(llm)
        code, name = await detector.detect(request.text)
        return DetectLanguageResponse(
            language=code,
            language_name=name,
            confidence="high",
        )
    except Exception as e:
        logger.error(f"Language detection error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Language detection unavailable.")


@router.post("/translate", response_model=TranslateResponse)
async def translate(request: TranslateRequest):
    """Translate text between languages."""
    try:
        # Validate language codes
        if request.source_language not in SUPPORTED_LANGUAGES and request.source_language != "auto":
            raise HTTPException(status_code=400, detail=f"Unsupported source language: {request.source_language}")
        if request.target_language not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail=f"Unsupported target language: {request.target_language}")

        llm = get_llm_provider()
        translator = TranslationService(llm)
        source_name = SUPPORTED_LANGUAGES.get(request.source_language, request.source_language)
        target_name = SUPPORTED_LANGUAGES.get(request.target_language, request.target_language)

        translated = await translator.translate(
            text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
            source_name=source_name,
            target_name=target_name,
        )

        return TranslateResponse(
            translated_text=translated,
            source_language=request.source_language,
            target_language=request.target_language,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Translation error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Translation service unavailable.")


@router.get("/languages")
async def list_languages():
    """Return all supported languages."""
    return {
        "languages": [
            {"code": code, "name": name}
            for code, name in SUPPORTED_LANGUAGES.items()
        ]
    }
