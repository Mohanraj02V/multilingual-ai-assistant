import logging
from fastapi import APIRouter

from app.models.schemas import HealthResponse
from app.services.llm.factory import get_llm_provider
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check — verifies the backend and LLM availability."""
    try:
        llm = get_llm_provider()
        available = await llm.is_available()
        return HealthResponse(
            status="ok",
            llm_provider=llm.provider_name,
            llm_available=available,
            model=llm.model_name,
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthResponse(
            status="degraded",
            llm_provider=settings.llm_provider,
            llm_available=False,
        )
