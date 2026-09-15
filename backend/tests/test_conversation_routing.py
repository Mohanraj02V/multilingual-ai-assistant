"""
Regression test for ConversationService multilingual tier routing.

This test was added to prevent a recurrence of the bug where the service
always generated English answers regardless of detected language.

Verified behavior:
- High-resource languages (en, es, fr, de, pt, it): generate() called once directly
  in target language; from_english() is NEVER called; ChatResponse.language == detected_lang.
- Indic/other languages: generate() called once in English; from_english() called once;
  ChatResponse.language == detected_lang (not "en").
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.services.conversation import ConversationService, HIGH_RESOURCE_LANGS
from app.models.schemas import ChatRequest, ChatResponse


def make_mock_llm(generate_return: str = "Answer text") -> MagicMock:
    llm = MagicMock()
    llm.generate = AsyncMock(return_value=generate_return)
    # stream_generate needs to be an async generator
    async def mock_stream_generate(*args, **kwargs):
        yield generate_return
    llm.stream_generate = mock_stream_generate
    return llm


def make_mock_request(message: str = "Tell me about the company", language: str = "en") -> ChatRequest:
    return ChatRequest(message=message, language=language, conversation=[])


class MockDocs:
    id = "doc1"
    title = "Company Overview"


@pytest.mark.asyncio
async def test_high_resource_english_no_translation():
    """English query: generate() called once; from_english() never called; language='en'."""
    llm = make_mock_llm("Here is info about the company.")
    service = ConversationService(llm)

    # Patch dependencies
    service._lang_detector.detect = AsyncMock(return_value=("en", "English"))
    service._lang_detector.get_language_name = MagicMock(return_value="English")
    service._translator.to_english = AsyncMock(return_value="Tell me about the company")
    service._translator.from_english = AsyncMock(return_value="should not be called")

    with patch("app.services.conversation.retrieval_service") as mock_retrieval:
        mock_doc = MockDocs()
        mock_retrieval.retrieve = AsyncMock(return_value=[mock_doc])
        mock_retrieval.format_context = MagicMock(return_value="Context text")

        response = await service.process(make_mock_request(language="en"))

    assert response.language == "en"
    llm.generate.assert_called_once()
    service._translator.from_english.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("lang_code,lang_name", [
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
])
async def test_high_resource_non_english_generates_directly(lang_code: str, lang_name: str):
    """High-resource non-English: generate() called once with lang instruction; from_english() not called; language==lang_code."""
    llm = make_mock_llm(f"Respuesta en {lang_name}.")
    service = ConversationService(llm)

    service._lang_detector.detect = AsyncMock(return_value=(lang_code, lang_name))
    service._lang_detector.get_language_name = MagicMock(return_value=lang_name)
    service._translator.to_english = AsyncMock(return_value="Tell me about the company")
    service._translator.from_english = AsyncMock(return_value="should not be called")

    with patch("app.services.conversation.retrieval_service") as mock_retrieval:
        mock_doc = MockDocs()
        mock_retrieval.retrieve = AsyncMock(return_value=[mock_doc])
        mock_retrieval.format_context = MagicMock(return_value="Context text")

        response = await service.process(make_mock_request(language=lang_code))

    # Language in response must match detected language
    assert response.language == lang_code
    # generate() called once (direct in-language generation)
    llm.generate.assert_called_once()
    # Translation from English must NOT have been called
    service._translator.from_english.assert_not_called()
    # The system prompt for generate() should instruct the model to respond in the target language
    call_kwargs = llm.generate.call_args
    system_prompt_used = call_kwargs[1].get('system_prompt') or call_kwargs[0][0]
    assert lang_name in system_prompt_used


@pytest.mark.asyncio
@pytest.mark.parametrize("lang_code,lang_name", [
    ("ta", "Tamil"),
    ("hi", "Hindi"),
    ("te", "Telugu"),
    ("ml", "Malayalam"),
    ("kn", "Kannada"),
])
async def test_indic_language_generates_english_then_translates(lang_code: str, lang_name: str):
    """Indic language: generate() called in English; from_english() called once; language==lang_code (not 'en')."""
    english_answer = "Here is info about the company in English."
    translated_answer = f"Translated answer in {lang_name}."
    llm = make_mock_llm(english_answer)
    service = ConversationService(llm)

    service._lang_detector.detect = AsyncMock(return_value=(lang_code, lang_name))
    service._lang_detector.get_language_name = MagicMock(return_value=lang_name)
    service._translator.to_english = AsyncMock(return_value="Tell me about the company")
    service._translator.from_english = AsyncMock(return_value=translated_answer)

    with patch("app.services.conversation.retrieval_service") as mock_retrieval:
        mock_doc = MockDocs()
        mock_retrieval.retrieve = AsyncMock(return_value=[mock_doc])
        mock_retrieval.format_context = MagicMock(return_value="Context text")

        response = await service.process(make_mock_request(language=lang_code))

    # Language in response must be the target Indic language, NOT "en"
    assert response.language == lang_code, f"Expected language={lang_code}, got {response.language}"
    # LLM generate() must have been called exactly once (for English generation)
    llm.generate.assert_called_once()
    # The English generation system prompt must instruct English only
    call_kwargs = llm.generate.call_args
    system_prompt_used = call_kwargs[1].get('system_prompt') or call_kwargs[0][0]
    assert "English only" in system_prompt_used
    # from_english must have been called with the English answer and correct target language
    service._translator.from_english.assert_called_once()
    from_english_args = service._translator.from_english.call_args
    assert from_english_args[0][0] == english_answer.strip() or \
           from_english_args[1].get('text') == english_answer.strip()
    # Response content must be the translated (not English) answer
    assert response.answer == translated_answer.strip()


@pytest.mark.asyncio
async def test_no_context_returns_english_fallback():
    """When no documents found, returns NO_CONTEXT_RESPONSE in English regardless of detected language."""
    from app.services.conversation import NO_CONTEXT_RESPONSE
    llm = make_mock_llm()
    service = ConversationService(llm)

    service._lang_detector.detect = AsyncMock(return_value=("ta", "Tamil"))
    service._lang_detector.get_language_name = MagicMock(return_value="Tamil")
    service._translator.to_english = AsyncMock(return_value="Tell me about the company")

    with patch("app.services.conversation.retrieval_service") as mock_retrieval:
        mock_retrieval.retrieve = AsyncMock(return_value=[])  # No docs

        response = await service.process(make_mock_request(language="ta"))

    # Fallback must be English
    assert response.language == "en"
    assert response.answer == NO_CONTEXT_RESPONSE
    # No LLM generation should have happened
    llm.generate.assert_not_called()


@pytest.mark.asyncio
async def test_english_hardcode_regression():
    """
    Regression: previously the service hardcoded language='en' for ALL responses.
    This test verifies that a Tamil query does NOT get language='en' in the response.
    It SHOULD have failed against the old implementation.
    """
    llm = make_mock_llm("Here is company info in English.")
    service = ConversationService(llm)

    service._lang_detector.detect = AsyncMock(return_value=("ta", "Tamil"))
    service._lang_detector.get_language_name = MagicMock(return_value="Tamil")
    service._translator.to_english = AsyncMock(return_value="Tell me about the company")
    service._translator.from_english = AsyncMock(return_value="நிறுவனம் பற்றிய தகவல்.")

    with patch("app.services.conversation.retrieval_service") as mock_retrieval:
        mock_doc = MockDocs()
        mock_retrieval.retrieve = AsyncMock(return_value=[mock_doc])
        mock_retrieval.format_context = MagicMock(return_value="Context text")

        response = await service.process(make_mock_request(language="ta"))

    # This would have been "en" in the broken version
    assert response.language == "ta", (
        f"REGRESSION: response.language should be 'ta', got '{response.language}'. "
        "This means the English-hardcode bug has returned."
    )
    assert response.language != "en", "Language must not be hardcoded to 'en' for Tamil queries"
