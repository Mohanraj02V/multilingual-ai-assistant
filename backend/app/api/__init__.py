from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.stt import router as stt_router

__all__ = ["chat_router", "health_router", "stt_router"]
