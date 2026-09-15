import logging
from typing import List, Dict, Tuple

from app.services.llm.base import LLMProvider
from app.services.retrieval import retrieval_service, KnowledgeDocument
from app.services.language_detection import LanguageDetectionService
from app.services.translation import TranslationService
from app.models.schemas import ChatRequest, ChatResponse, SourceDocument, ConversationTurn
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful company knowledge assistant for TechCorp Solutions.

Answer the user's question using ONLY the provided knowledge context below.

STRICT RULES:
1. Only use information from the provided context to answer.
2. If the answer cannot be found in the context, say clearly: "I don't have enough information to answer that question."
3. Never invent company policies, prices, addresses, contact details, products, employees, or any other facts.
4. Keep answers concise, friendly, and helpful.
5. Do not mention that you are using a "knowledge context" or "provided documents" — answer naturally.
{lang_instruction}

Knowledge Context:
{context}"""

NO_CONTEXT_RESPONSE = "I don't have enough information to answer that question. Please contact our support team at support@techcorp.com for assistance."

# High-resource languages: the LLM generates directly in the target language.
# All other languages (Indic etc.) go through English generation + translation.
HIGH_RESOURCE_LANGS = {"en", "es", "fr", "de", "pt", "it"}


class ConversationService:
    """Orchestrates the full multilingual conversation pipeline:

    1. Detect user language
    2. Translate user message to English (for retrieval + LLM reasoning)
    3. Retrieve relevant knowledge documents
    4. Generate answer:
       - High-resource languages (en, es, fr, de, pt, it): generate directly in target language
       - Indic/other languages: generate in English, then translate to target language
    5. Return structured response with correct language code
    """

    def __init__(self, llm_provider: LLMProvider):
        self._llm = llm_provider
        self._lang_detector = LanguageDetectionService(llm_provider)
        self._translator = TranslationService(llm_provider)

    async def process(self, request: ChatRequest) -> ChatResponse:
        """Process a chat request end-to-end."""

        user_message = request.message.strip()

        # --- Step 1: Determine language ---
        if request.language and request.language != "auto":
            detected_lang = request.language
            lang_name = self._lang_detector.get_language_name(detected_lang)
            logger.info(f"User-specified language: {detected_lang} ({lang_name})")
        else:
            detected_lang, lang_name = await self._lang_detector.detect(user_message)
            logger.info(f"Auto-detected language: {detected_lang} ({lang_name})")

        # --- Step 2: Translate to English for retrieval + LLM reasoning ---
        if detected_lang != "en":
            english_message = await self._translator.to_english(
                user_message, detected_lang, lang_name
            )
            logger.info(f"Translated to English: {english_message}")
        else:
            english_message = user_message

        # --- Step 3: Retrieve relevant knowledge ---
        docs = await retrieval_service.retrieve(english_message)
        logger.info(f"Retrieved {len(docs)} documents")

        if not docs:
            # No relevant knowledge found — English-only fallback.
            # Decision: stays English-only. The message is a generic "contact support"
            # prompt that doesn't contain factual knowledge worth translating.
            logger.info("No context found; returning NO_CONTEXT_RESPONSE in English.")
            return ChatResponse(
                answer=NO_CONTEXT_RESPONSE,
                language="en",
                detected_language=detected_lang,
                sources=[],
            )

        # --- Step 4: Build context and conversation history ---
        context = retrieval_service.format_context(docs)
        history = self._build_history(request.conversation)

        # --- Step 5: Generate answer (language-tiered) ---
        sources = [SourceDocument(id=doc.id, title=doc.title) for doc in docs]

        if detected_lang in HIGH_RESOURCE_LANGS:
            # Single-call path: generate answer directly in target language.
            lang_instruction = (
                f"\n6. Respond in {lang_name} only."
                if detected_lang != "en"
                else "\n6. Respond in English."
            )
            system_prompt = SYSTEM_PROMPT.format(
                context=context, lang_instruction=lang_instruction
            )
            logger.info(f"High-resource path: generating directly in {lang_name}")
            try:
                raw_answer = await self._llm.generate(
                    system_prompt=system_prompt,
                    user_message=english_message,
                    conversation_history=history,
                )
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
                raise

            return ChatResponse(
                answer=raw_answer.strip(),
                language=detected_lang,
                detected_language=detected_lang,
                sources=sources,
            )

        else:
            # Two-call path for Indic and other languages:
            # 1. Generate English answer (best reasoning quality with English-trained LLM).
            # 2. Translate English answer to target language.
            system_prompt = SYSTEM_PROMPT.format(
                context=context, lang_instruction="\n6. Respond in English only."
            )
            logger.info(f"Indic/other path: generating in English, then translating to {lang_name}")
            try:
                english_answer = await self._llm.generate(
                    system_prompt=system_prompt,
                    user_message=english_message,
                    conversation_history=history,
                )
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
                raise

            logger.info(f"English answer generated. Translating to {lang_name}...")
            try:
                final_answer = await self._translator.from_english(
                    english_answer.strip(), detected_lang, lang_name
                )
            except Exception as e:
                logger.error(f"Translation to {lang_name} failed, returning English fallback: {e}")
                final_answer = english_answer  # Graceful degradation

            return ChatResponse(
                answer=final_answer.strip(),
                language=detected_lang,
                detected_language=detected_lang,
                sources=sources,
            )

    def _build_history(
        self, conversation: List[ConversationTurn]
    ) -> List[Dict[str, str]]:
        """Convert conversation turns to LLM message format."""
        max_turns = settings.max_conversation_turns
        recent = conversation[-max_turns:] if len(conversation) > max_turns else conversation
        return [
            {"role": turn.role, "content": turn.content}
            for turn in recent
        ]
