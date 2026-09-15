# Multilingual AI Voice & Text Assistant

A production-ready, full-stack application that acts as a multilingual AI assistant. It supports speech-to-text, text-to-speech, and answers questions intelligently in 18+ languages by querying a local knowledge base.

## Features

- **Voice & Text Input**: Speak your questions using the microphone or type them.
- **Multilingual Support**: Supports English, Tamil, Hindi, Spanish, French, Japanese, and many more. Automatically detects language.
- **Voice Output**: The assistant reads answers aloud in the detected language (can be paused/stopped).
- **Local Knowledge Base**: Grounded generation. Answers only using the provided `knowledge.json` data.
- **Privacy-First (Local LLM)**: Uses Ollama by default for 100% local, offline processing without sending data to third parties.
- **Responsive Premium UI**: Built with React, Tailwind CSS, and a dark/glassmorphic aesthetic.
- **Modular Architecture**: Easy to swap out STT, TTS, LLM providers, and Retrieval mechanisms.

---

## Architecture Overview

```text
UI (React/Tailwind)
       ↓
API (FastAPI)
       ↓
Conversation Service
       ↓
Language Detection Service
       ↓
Retrieval Service (Searches knowledge.json)
       ↓
LLM Service (Ollama Llama 3.2 via abstraction)
       ↓
Response (Text translated back to original language)
       ↓
TTS (Web Speech Synthesis)
```

---

## 1. Prerequisites

- **Python 3.9+**
- **Node.js 18+** (and `npm` or `yarn`)
- **Ollama** installed on your system (for local LLM).

---

## 2. Setting up Ollama (Local AI)

1. Download and install [Ollama](https://ollama.com/).
2. Start the Ollama application.
3. Open a terminal and pull the Llama 3.2 model (or any other lightweight model):
   ```bash
   ollama run llama3.2
   ```
   *You can exit the chat prompt once the model is downloaded. Ollama runs automatically in the background at `http://localhost:11434`.*

---

## 3. Backend Setup (FastAPI)

1. Open a terminal and navigate to the `backend` folder:
   ```bash
   cd multilingual-ai-assistant/backend
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   
   # Windows:
   .\venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create your environment variables file:
   ```bash
   cp .env.example .env
   ```
   *(Ensure `LLM_PROVIDER=ollama` and `OLLAMA_MODEL=llama3.2` match your setup).*

5. Start the backend server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   The backend will be available at `http://localhost:8000`.

---

## 4. Frontend Setup (React/Vite)

1. Open a new terminal and navigate to the `frontend` folder:
   ```bash
   cd multilingual-ai-assistant/frontend
   ```

2. Install the dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```
   The frontend will be available at `http://localhost:5173`.

---

## 5. Editing the Knowledge Base

The assistant uses a local knowledge base to answer questions securely without hallucinating.

1. Open `backend/data/knowledge.json`.
2. Add or modify the FAQ entries using this format:
   ```json
   {
     "id": "custom-policy",
     "title": "Custom Policy",
     "content": "This is the content the AI will read to answer questions."
   }
   ```
3. The backend automatically loads this file when you ask questions.

---

## 6. Supported Languages

The application uses browser-native STT/TTS and LLM capabilities for the following languages:

English (`en`), Tamil (`ta`), Hindi (`hi`), Telugu (`te`), Malayalam (`ml`), Kannada (`kn`), Bengali (`bn`), Marathi (`mr`), Spanish (`es`), French (`fr`), German (`de`), Japanese (`ja`), Chinese (`zh`), Arabic (`ar`), Portuguese (`pt`), Russian (`ru`), Korean (`ko`), Italian (`it`).

*Note: Voice capabilities (STT/TTS) depend on the browser's supported languages and installed OS language packs.*

---

## 7. Troubleshooting

- **Microphone Access Denied:** Ensure you are accessing the app via `localhost` or HTTPS. Browsers block microphone access on unencrypted connections.
- **LLM Not Responding:** Ensure Ollama is running and you have downloaded the `llama3.2` model (`ollama list`). Check the backend console for connection errors.
- **Voice Output (TTS) Silent:** Some browsers require a user interaction (click/touch) before they allow audio playback. Click the "Listen" button on the message if it doesn't play automatically.

---

## 8. Future Upgrades (Production Considerations)

The services are strictly abstracted. To scale to a cloud production environment:
1. **LLM**: Create `app/services/llm/openai.py` implementing `LLMProvider` and update `.env` to `LLM_PROVIDER=openai`.
2. **Vector DB**: Update `app/services/retrieval.py` to connect to PostgreSQL (pgvector) or ChromaDB instead of loading `knowledge.json`.
3. **Speech**: Update `frontend/src/services/speechToText.ts` to POST audio blobs to a Whisper API instead of using the Browser Web Speech API.
