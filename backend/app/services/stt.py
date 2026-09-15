import os
import io
import math
import logging
from typing import Tuple, Optional
from faster_whisper import WhisperModel

from app.services.language_detection import detect_by_script
from app.config import settings

logger = logging.getLogger(__name__)

class WhisperSTTService:
    def __init__(self):
        self._model_size = os.environ.get("STT_MODEL_SIZE", "small")
        self._model: Optional[WhisperModel] = None

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            logger.info(f"Loading Whisper model '{self._model_size}' (CPU int8)...")
            self._model = WhisperModel(
                self._model_size,
                device="cpu",
                compute_type="int8",
                download_root="./data/whisper-model"
            )
            logger.info("Whisper model loaded successfully.")
        return self._model

    def warmup(self):
        """Warm up the model with a tiny silent audio clip."""
        try:
            model = self._get_model()
            # 0.1s silent PCM 16kHz WAV
            import wave
            import struct
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                num_samples = int(16000 * 0.1)
                wf.writeframes(struct.pack(f'<{num_samples}h', *([0] * num_samples)))
            
            buf.seek(0)
            segments, info = model.transcribe(buf, beam_size=1)
            _ = list(segments)
            logger.info("Whisper STT model warmed up successfully.")
        except Exception as e:
            logger.error(f"Failed to warmup Whisper model: {e}")

    def transcribe(self, audio_bytes: bytes, language_hint: Optional[str] = None) -> Tuple[str, str, float]:
        """
        Transcribe audio bytes (webm, wav, etc.) to text.
        Returns: (transcript, detected_language, confidence)
        """
        model = self._get_model()
        
        # faster-whisper can take a file-like object and uses PyAV internally
        buf = io.BytesIO(audio_bytes)
        
        segments, info = model.transcribe(
            buf,
            beam_size=settings.stt_beam_size,
            language=language_hint if language_hint and language_hint != "auto" else None,
            vad_filter=True
        )
        
        transcript = ""
        no_speech_probs = []
        for segment in segments:
            transcript += segment.text + " "
            no_speech_probs.append(segment.no_speech_prob)
            
        transcript = transcript.strip()
        
        # Calculate confidence
        if no_speech_probs:
            avg_no_speech_prob = sum(no_speech_probs) / len(no_speech_probs)
            confidence = 1.0 - avg_no_speech_prob
        else:
            confidence = 0.0
            
        # Cross-validate language detection with script check
        detected_language = info.language
        script_lang = detect_by_script(transcript)
        
        if script_lang and script_lang != detected_language:
            logger.info(f"Overriding Whisper detected language '{detected_language}' with script-detected '{script_lang}'")
            detected_language = script_lang
            
        return transcript, detected_language, confidence

whisper_stt_service = WhisperSTTService()
