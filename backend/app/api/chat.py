import logging
import httpx
from fastapi import APIRouter, HTTPException, Request, Depends, Header
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.services.retrieval import retrieval_service

limiter = Limiter(key_func=get_remote_address)
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
@limiter.limit("10/minute")
async def chat(request: Request, payload: ChatRequest):
    """Main chat endpoint — processes text/voice input and returns an answer."""
    try:
        llm = get_llm_provider()
        service = ConversationService(llm)
        response = await service.process(payload)
        return response
    except httpx.ConnectError as e:
        logger.error(f"Chat API Connect Error: {e}")
        raise HTTPException(
            status_code=503, 
            detail="AI backend is unreachable. Please ensure Ollama is running."
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"Chat API HTTP Error: {e}")
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=503, 
                detail=f"Model not found. Please run 'ollama pull {settings.ollama_model}'."
            )
        raise HTTPException(status_code=503, detail="AI service encountered an HTTP error.")
    except httpx.ReadTimeout as e:
        logger.error("Chat API generation timed out")
        raise HTTPException(status_code=504, detail="AI generation timed out. The model may be overloaded or the prompt too large.")
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="The AI service is currently unavailable. Please try again."
        )

def verify_admin_key(x_api_key: str = Header(None)):
    if settings.environment == "production":
        if not settings.admin_api_key or settings.admin_api_key in ["", "dev-secret-key"]:
            logger.critical("Admin API key is unset or insecure in production mode. Reload endpoint disabled.")
            raise HTTPException(status_code=503, detail="Admin endpoint disabled due to insecure configuration.")
            
    if x_api_key != settings.admin_api_key and settings.admin_api_key != "":
        raise HTTPException(status_code=401, detail="Invalid API Key")
        
@router.post("/admin/reload-knowledge")
async def reload_knowledge(_ = Depends(verify_admin_key)):
    """Reload the knowledge base documents into ChromaDB."""
    try:
        await retrieval_service.initialize()
        return {"message": "Knowledge base reloaded successfully."}
    except Exception as e:
        logger.exception("Failed to reload knowledge base")
        raise HTTPException(status_code=500, detail="Failed to reload knowledge base.")


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
