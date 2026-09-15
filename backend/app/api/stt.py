from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, status
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
    """
    try:
        audio_bytes = await audio.read()
        
        if not audio_bytes or len(audio_bytes) < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="no-speech"
            )
            
        transcript, detected_language, confidence = whisper_stt_service.transcribe(
            audio_bytes, 
            language_hint=language
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
