from pydantic import BaseModel, Field
from typing import List, Optional


class ConversationTurn(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    language: Optional[str] = None  # e.g. "en", "ta", "hi" — None = auto-detect
    conversation: List[ConversationTurn] = Field(default_factory=list)


class SourceDocument(BaseModel):
    id: str
    title: str


class ChatResponse(BaseModel):
    answer: str
    language: str
    detected_language: Optional[str] = None
    sources: List[SourceDocument] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    llm_available: bool
    model: Optional[str] = None


class DetectLanguageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


class DetectLanguageResponse(BaseModel):
    language: str
    language_name: str
    confidence: str


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    source_language: str
    target_language: str


class TranslateResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str
