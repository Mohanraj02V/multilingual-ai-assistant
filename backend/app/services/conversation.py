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
5. Respond in the language specified in the instruction.
6. Do not mention that you are using a "knowledge context" or "provided documents" — answer naturally.

Knowledge Context:
{context}"""

NO_CONTEXT_RESPONSE = "I don't have enough information to answer that question. Please contact our support team at support@techcorp.com for assistance."


class ConversationService:
    """Orchestrates the full multilingual conversation pipeline:
    
    1. Detect user language
    2. Translate user message to English (if needed)
    3. Retrieve relevant knowledge documents
    4. Generate answer via LLM
    5. Translate answer back to user's language (if needed)
    6. Return structured response
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

        # --- Step 2: Translate to English for retrieval + LLM ---
        if detected_lang != "en":
            english_message = await self._translator.to_english(
                user_message, detected_lang, lang_name
            )
            logger.info(f"Translated to English: {english_message}")
        else:
            english_message = user_message

        # --- Step 3: Retrieve relevant knowledge ---
        docs = retrieval_service.retrieve(english_message)
        logger.info(f"Retrieved {len(docs)} documents")

        if not docs:
            # No relevant knowledge found — answer in user's language
            if detected_lang != "en":
                answer = await self._translator.from_english(
                    NO_CONTEXT_RESPONSE, detected_lang, lang_name
                )
            else:
                answer = NO_CONTEXT_RESPONSE

            return ChatResponse(
                answer=answer,
                language=detected_lang,
                detected_language=detected_lang,
                sources=[],
            )

        # --- Step 4: Build context and conversation history ---
        context = retrieval_service.format_context(docs)

        # Prepare language instruction for system prompt
        lang_instruction = (
            f"\nIMPORTANT: Respond in {lang_name} language only."
            if detected_lang != "en"
            else ""
        )

        system_prompt = SYSTEM_PROMPT.format(context=context) + lang_instruction

        # Build conversation history (capped at max turns)
        history = self._build_history(request.conversation)

        # --- Step 5: Generate answer ---
        try:
            raw_answer = await self._llm.generate(
                system_prompt=system_prompt,
                user_message=english_message if detected_lang == "en" else f"{user_message}\n[Please respond in {lang_name}]",
                conversation_history=history,
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

        # --- Step 6: Return response ---
        sources = [
            SourceDocument(id=doc.id, title=doc.title) for doc in docs
        ]

        return ChatResponse(
            answer=raw_answer.strip(),
            language=detected_lang,
            detected_language=detected_lang,
            sources=sources,
        )

    def _build_history(
        self, conversation: List[ConversationTurn]
    ) -> List[Dict[str, str]]:
        """Convert conversation turns to LLM message format."""
        # Limit history to avoid token overflow
        max_turns = settings.max_conversation_turns
        recent = conversation[-max_turns:] if len(conversation) > max_turns else conversation

        return [
            {"role": turn.role, "content": turn.content}
            for turn in recent
        ]
