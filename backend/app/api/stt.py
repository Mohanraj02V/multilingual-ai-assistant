from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, status
import asyncio
import logging
from typing import Optional

from app.services.stt import whisper_stt_service
from app.models.schemas import STTResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stt", tags=["stt"])

@router.post("/transcribe", response_model=STTResponse)
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(...),
    language: Optional[str] = Form(None)
):
    """
    Transcribe uploaded audio file using Whisper.

    WhisperModel.transcribe() is CPU-bound and blocking — we offload it to a
    thread via asyncio.to_thread so it doesn't stall the event loop (health checks,
    other API requests) during transcription.
    """
    try:
        audio_bytes = await audio.read()

        if not audio_bytes or len(audio_bytes) < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="no-speech"
            )

        # Offload CPU-bound Whisper work to a thread — keeps the event loop free.
        transcript, detected_language, confidence = await asyncio.to_thread(
            whisper_stt_service.transcribe,
            audio_bytes,
            language
        )

        if confidence < 0.3:  # Threshold for "no speech"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="no-speech"
            )

        return STTResponse(
            transcript=transcript,
            detected_language=detected_language,
            confidence=confidence
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("STT Transcription failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}"
        )
