import logging
import json
import httpx
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request, Depends, Header
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.services.retrieval import retrieval_service

limiter = Limiter(key_func=get_remote_address)

from app.models.schemas import (
    ChatRequest, ChatResponse,
    DetectLanguageRequest, DetectLanguageResponse,
    TranslateRequest, TranslateResponse,
)
from app.services.llm.factory import get_llm_provider
from app.services.conversation import ConversationService, HIGH_RESOURCE_LANGS, SYSTEM_PROMPT, NO_CONTEXT_RESPONSE
from app.services.language_detection import LanguageDetectionService, SUPPORTED_LANGUAGES
from app.services.translation import TranslationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


async def _stream_conversation(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Core SSE generator for the /api/chat endpoint.

    SSE event format:
      data: <token>\\n\\n           — streaming content token
      data: [DONE]\\n\\n            — normal end of stream
      event: error\\ndata: <msg>   — error event (mid-stream failure)

    Metadata (language, sources) is sent as response headers before the stream starts.
    This keeps a single response-handling code path on the frontend for all cases
    (including the NO_CONTEXT_RESPONSE fallback, which is emitted as a single chunk).
    """
    llm = get_llm_provider()
    lang_detector = LanguageDetectionService(llm)
    translator = TranslationService(llm)

    user_message = request.message.strip()

    try:
        # Step 1: Detect language
        if request.language and request.language != "auto":
            detected_lang = request.language
            lang_name = lang_detector.get_language_name(detected_lang)
        else:
            detected_lang, lang_name = await lang_detector.detect(user_message)
        logger.info(f"SSE chat: detected_lang={detected_lang} ({lang_name})")

        # Step 2: Translate to English for retrieval
        if detected_lang != "en":
            english_message = await translator.to_english(user_message, detected_lang, lang_name)
        else:
            english_message = user_message

        # Step 3: Retrieve knowledge
        docs = await retrieval_service.retrieve(english_message)
        sources = [{"id": d.id, "title": d.title} for d in docs]

        # Emit metadata header event so frontend knows language + sources immediately
        meta = json.dumps({"detected_language": detected_lang, "language": detected_lang, "sources": sources})
        yield f"event: meta\ndata: {meta}\n\n"

        if not docs:
            # No context — emit the fallback as a single content chunk, then done.
            yield f"data: {NO_CONTEXT_RESPONSE}\n\n"
            yield "data: [DONE]\n\n"
            return

        context = retrieval_service.format_context(docs)
        history_service = ConversationService(llm)
        history = history_service._build_history(request.conversation)

        if detected_lang in HIGH_RESOURCE_LANGS:
            # Single-call: stream directly in target language
            lang_instruction = (
                f"\n6. Respond in {lang_name} only."
                if detected_lang != "en"
                else "\n6. Respond in English."
            )
            system_prompt = SYSTEM_PROMPT.format(context=context, lang_instruction=lang_instruction)
            logger.info(f"SSE high-resource path: streaming in {lang_name}")

            async for token in llm.stream_generate(system_prompt, english_message, history):
                yield f"data: {json.dumps(token)}\n\n"

        else:
            # Two-phase Indic path:
            # Phase 1: Generate English internally (signal "thinking" to frontend)
            # Phase 2: Stream the translation to the frontend
            system_prompt = SYSTEM_PROMPT.format(
                context=context, lang_instruction="\n6. Respond in English only."
            )
            logger.info(f"SSE Indic path: generating English internally, then streaming {lang_name} translation")

            # Signal to frontend that internal English generation is in progress
            yield f"event: thinking\ndata: {json.dumps({'message': 'Thinking...'})}\n\n"

            # Collect full English answer (not streamed to user)
            english_answer_parts = []
            async for token in llm.stream_generate(system_prompt, english_message, history):
                english_answer_parts.append(token)
            english_answer = "".join(english_answer_parts).strip()

            if not english_answer:
                yield f"event: error\ndata: {json.dumps({'detail': 'Generation produced empty output.'})}\n\n"
                return

            # Signal translation starting
            yield f"event: translating\ndata: {json.dumps({'message': 'Translating...'})}\n\n"

            # Stream the translation
            async for token in translator.stream_from_english(english_answer, detected_lang, lang_name):
                yield f"data: {json.dumps(token)}\n\n"

        yield "data: [DONE]\n\n"

    except (httpx.ConnectError, httpx.RequestError) as e:
        logger.error(f"SSE stream: Ollama connection error: {e}")
        yield f"event: error\ndata: {json.dumps({'detail': 'AI backend is unreachable.'})}\n\n"
    except httpx.HTTPStatusError as e:
        logger.error(f"SSE stream: Ollama HTTP error {e.response.status_code}")
        yield f"event: error\ndata: {json.dumps({'detail': 'AI service HTTP error.'})}\n\n"
    except Exception as e:
        logger.error(f"SSE stream: unexpected error: {e}", exc_info=True)
        yield f"event: error\ndata: {json.dumps({'detail': 'The AI service is currently unavailable.'})}\n\n"


@router.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, payload: ChatRequest):
    """
    Main chat endpoint — returns an SSE stream of tokens.

    Response headers carry metadata (detected_language, language, sources) as a
    JSON-encoded `X-Chat-Meta` header set before the stream starts, so the frontend
    has a single code path regardless of language tier or fallback.

    Rate limiting: slowapi's limit decorator correctly enforces the rate limit on
    StreamingResponse — the limit is checked before the response body is generated,
    so the 10/minute limit is applied consistently.
    """
    return StreamingResponse(
        _stream_conversation(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
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
