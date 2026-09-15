import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.chat import router as chat_router, limiter
from app.api.health import router as health_router
from app.api.stt import router as stt_router

from app.services.llm.factory import get_llm_provider
from app.services.retrieval import retrieval_service
import time

from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

# Configure logging
if settings.environment == "production":
    from pythonjsonlogger import jsonlogger
    logger = logging.getLogger()
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info(f"Starting Multilingual AI Assistant Backend")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"Ollama URL: {settings.ollama_base_url}")
    logger.info(f"Model: {settings.ollama_model}")
    
    # Warmup models
    llm = get_llm_provider()
    if await llm.is_available():
        logger.info("Ollama is available. Warming up chat model...")
        start_time = time.time()
        try:
            # Send trivial ping to load the chat model into memory
            await llm.generate("You are a warmup bot. Say hi.", "hi")
            warmup_time = time.time() - start_time
            logger.info(f"Chat model warmed up in {warmup_time:.2f}s via explicit ping.")
        except Exception as e:
            logger.error(f"Chat model warmup failed: {e}")
            
        # Initialize RAG retrieval (loads docs and creates ChromaDB collection)
        logger.info("Initializing retrieval service and warming up embedding model...")
        try:
            await retrieval_service.initialize()
            logger.info("Retrieval service initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize retrieval service: {e}")
            
        # Warmup Whisper STT
        from app.services.stt import whisper_stt_service
        logger.info("Warming up Whisper STT model...")
        whisper_stt_service.warmup()
            
    else:
        logger.error(f"CRITICAL: Ollama is not reachable at {settings.ollama_base_url}.")
        logger.error(f"Please ensure Ollama is running and run 'ollama pull {settings.ollama_model}' and 'ollama pull {settings.ollama_embedding_model}'.")
        
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Multilingual AI Assistant API",
    description="Production-ready multilingual AI voice & text assistant backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# Setup SlowAPI rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS — allow frontend dev server and production origins
allowed_origins = [o.strip() for o in settings.allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Global error handler — never expose raw stack traces
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )


# Register routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(stt_router)


@app.get("/")
async def root():
    return {"message": "Multilingual AI Assistant API", "docs": "/docs"}
