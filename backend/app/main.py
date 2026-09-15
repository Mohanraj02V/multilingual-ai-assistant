import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.chat import router as chat_router
from app.api.health import router as health_router

# Configure logging
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
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Multilingual AI Assistant API",
    description="Production-ready multilingual AI voice & text assistant backend",
    version="1.0.0",
    lifespan=lifespan,
)

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


@app.get("/")
async def root():
    return {"message": "Multilingual AI Assistant API", "docs": "/docs"}
