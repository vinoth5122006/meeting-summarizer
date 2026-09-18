# Vocalis AI — Comprehensive Workflow Architecture & Tech Stack Documentation

## 1. Executive Summary

**Vocalis AI** is an enterprise-grade Meeting Intelligence and Audio Summarization platform. It processes multi-speaker meeting recordings (MP3, WAV, M4A, FLAC, AAC, OGG) and automatically generates:
1. **Verbatim Transcript with Speaker Diarization**: Time-stamped utterances categorized by individual speakers (Speaker A, Speaker B, etc.).
2. **Overall Executive Summary**: Contextual summary supporting bilingual code-switching (automatically generating natural **Tanglish** for Tamil-English mixed meetings, or English for pure English meetings).
3. **Person-Wise Summaries**: Breakdown of contributions, proposals, and arguments grouped by individual participant.
4. **Verbatim Action Items**: Strictly grounded task extraction identifying the precise work item, who raised it, and who it is assigned to.

---

## 2. Complete End-to-End Workflow Architecture

```
                               ┌─────────────────────────────────────────────────────────┐
                               │                    USER INTERFACE                       │
                               │  - Drag & Drop Audio Upload (MP3, WAV, M4A, FLAC, etc.) │
                               │  - Format & Size Validation (up to 50MB)                │
                               │  - Client-Side State & Async Fetch Handler              │
                               └──────────────────────────┬──────────────────────────────┘
                                                          │ HTTP POST /api/transcribe
                                                          │ (multipart/form-data)
                                                          ▼
                               ┌─────────────────────────────────────────────────────────┐
                               │                 FASTAPI API GATEWAY                     │
                               │  - Async Request Handling (`app.py`)                    │
                               │  - Temp File Storage (`tempfile`)                       │
                               │  - Environment API Key Resolution (`python-dotenv`)     │
                               └──────────────────────────┬──────────────────────────────┘
                                                          │
                                                          ▼
                               ┌─────────────────────────────────────────────────────────┐
                               │              SPEECH-TO-TEXT & DIARIZATION               │
                               │            (AssemblyAI SDK `assemblyai`)                │
                               │  - High-accuracy Speech Recognition                     │
                               │  - Multi-Speaker Diarization (`speaker_labels=True`)    │
                               │  - Time-stamped Utterances Generation                   │
                               └──────────────────────────┬──────────────────────────────┘
                                                          │
                                                          ▼
                               ┌─────────────────────────────────────────────────────────┐
                               │           LANGUAGE & SCRIPT DETECTION ENGINE            │
                               │  - Regex inspection for Tamil script (\u0B80-\u0BFF)    │
                               │  - Tanglish token vocabulary matching                   │
                               │  - Flags transcript as Bilingual (Tanglish) or English  │
                               └──────────────────────────┬──────────────────────────────┘
                                                          │
                                         ┌────────────────┴────────────────┐
                                         │                                 │
                            [OpenRouter API Key Available]   [No Key / Fallback Route]
                                         │                                 │
                                         ▼                                 ▼
         ┌──────────────────────────────────────────┐   ┌──────────────────────────────────────────┐
         │     LLM EXECUTIVE INTELLIGENCE           │   │    BUILT-IN NLP RULE-BASED ENGINE        │
         │  - GPT-4o-mini via OpenRouter            │   │  - Regex Action Verbs (CONCRETE_ACTION)  │
         │  - Formatted JSON response mode          │   │  - Tanglish Action Trigger Detector      │
         │  - Enforces Tanglish summary rule        │   │  - Conversational Noise & Ack Filter     │
         │  - Verbatim Action Grounding             │   │  - Speaker Task Assignment Logic         │
         └────────────────────┬─────────────────────┘   └────────────────────┬─────────────────────┘
                              │                                              │
                              └─────────────────────┬────────────────────────┘
                                                    │ Structured JSON Response Payload
                                                    ▼
                               ┌─────────────────────────────────────────────────────────┐
                               │               DYNAMIC FRONTEND RENDERING                │
                               │  - Interactive Audio Player Sync                        │
                               │  - Speaker Diarization Badges                           │
                               │  - Executive Overall Summary (Tanglish / English)        │
                               │  - Person-Wise Breakdown Accordion                      │
                               │  - Action Item Delegated Cards                          │
                               └─────────────────────────────────────────────────────────┘
```

### Stage-by-Stage Detailed Breakdown:

1. **User Ingestion**: The user uploads an audio recording via the web interface (`workspace.html`). Front-end validation (`script.js`) verifies audio file type and size.
2. **API Endpoint (`/api/transcribe`)**: FastAPI accepts the file via `UploadFile`, writes it temporarily to the host filesystem using Python's `tempfile` module, and resolves API credentials.
3. **Speech Diarization**: The file path is sent to AssemblyAI's cloud transcription service with `speaker_labels=True`. AssemblyAI processes the audio and returns utterance-level text mapped to speaker IDs.
4. **Bilingual Detection**: The transcript text is analyzed by `is_bilingual_or_tamil()`. If Tamil script characters or common Tanglish vocabulary tokens (`naan`, `neenga`, `romba`, `pannunga`, `anupuren`) are detected, the system marks the transcript as bilingual.
5. **Summarization & Task Extraction**:
   - **Primary LLM Engine**: Sends a structured JSON prompt to OpenRouter (`openai/gpt-4o-mini`). It enforces Tanglish for bilingual summaries and strictly grounds action items to verbatim spoken sentences.
   - **Built-in Fallback Engine**: If no LLM key is available or the request fails, the application uses regex rule matching (`CONCRETE_ACTION_RE`, `TANGLISH_ACTION_RE`, `MODAL_TASK_RE`, `NOISE_RE`, `ACKNOWLEDGEMENT_RE`) to parse sentences, eliminate filler/opinions, assign task owners, and generate the summary.
6. **UI Rendering**: The backend returns a JSON payload containing raw transcript, overall summary, person-wise summaries, action items, and timestamped utterances. The frontend dynamically populates the workspace dashboard.

---

## 3. Technology Stack & Library Specification

### A. Backend Framework & Web Server

| Technology / Library | Version | Purpose in Project | Why Chosen & Contribution |
| :--- | :--- | :--- | :--- |
| **Python** | `3.12+` | Core programming language | Offers an extensive ecosystem for AI integration, native async support, and clean string processing. |
| **FastAPI** | `0.115.0` | Asynchronous Web API Framework | Serves static assets (`/`), web pages (`/workspace`), and the `/api/transcribe` REST endpoint. Provides automatic request validation, fast performance, and native async support. |
| **Uvicorn** | `0.30.6` | ASGI Web Server | Serves the FastAPI application asynchronously in both local development and production (Render cloud). |
| **Python-Multipart** | `0.0.9` | Multipart Form Parser | Required by FastAPI to process streaming file uploads (`UploadFile`) directly from HTML forms. |
| **Python-Dotenv** | `1.0.1` | Environment Variable Manager | Reads configuration settings and API keys (`ASSEMBLYAI_API_KEY`, `OPENROUTER_API_KEY`) from local `.env` files without hardcoding credentials. |

---

### B. AI, Speech Processing & Natural Language Processing (NLP)

| Technology / Library | Version | Purpose in Project | Why Chosen & Contribution |
| :--- | :--- | :--- | :--- |
| **AssemblyAI SDK** | `1.5.2` | Speech-to-Text & Diarization Engine | Transcribes audio recordings into text and identifies distinct speakers (`Speaker A`, `Speaker B`) with start/end timestamps. |
| **OpenRouter API** | External API | LLM Intelligence Gateway | Connects to state-of-the-art models (`openai/gpt-4o-mini`) for executive summarization, structured JSON responses, and bilingual translation. |
| **Requests** | `2.32.3` | HTTP Client Library | Used to send HTTP POST payloads to the OpenRouter REST API and handle JSON responses securely. |
| **Python `re` (Regex)** | Built-in | Language Detection & Rule-Based NLP | Powers bilingual/Tanglish detection and the fallback action item extraction engine. Uses compiled regular expressions to separate actionable tasks from conversational noise. |

---

### C. Frontend Architecture & User Interface

| Technology / Library | Type | Purpose in Project | Why Chosen & Contribution |
| :--- | :--- | :--- | :--- |
| **HTML5** | Markup Language | Application Structure | Provides semantic markup for `index.html` (landing page) and `workspace.html` (interactive workspace). |
| **Vanilla CSS3** | Custom Stylesheet | Glassmorphic Responsive Design | Custom dark-theme styling (`style.css`), gradient borders, CSS Grid layout, and animated UI elements without external CSS framework overhead. |
| **Vanilla JavaScript ES6+** | Client-Side Script | Asynchronous UI & State Management | Handles file drag-and-drop events, API fetch calls, DOM updates, tab switching, copy-to-clipboard functionality, and interactive transcript playback. |
| **Google Fonts** | Web Typography | Fonts (`Inter`, `Plus Jakarta Sans`) | Delivers a clean, professional corporate aesthetic for meeting intelligence reports. |

---

### D. Infrastructure, Deployment & DevOps

| Tool / Platform | Configuration | Purpose in Project | Why Chosen & Contribution |
| :--- | :--- | :--- | :--- |
| **Render.com** | `render.yaml` | Cloud Hosting PaaS | Automatically builds and hosts the Python Web Service with SSL certificates and environment variable management. |
| **GitHub** | Git Remote Repository | Source Code Management & CI/CD | Houses source code (`vinoth5122006/meeting-summarizer`) and triggers auto-deployment on Render upon git push. |
| **`start.sh`** | Bash Script | Shell Execution Entrypoint | Resolves dynamic host `$PORT` environment variables on Render (`${PORT:-10000}`) and starts Uvicorn. |
| **`Procfile`** | Process Specification | Process Manager Directive | Specifies web process startup command (`web: bash start.sh`). |

---

## 4. Key Architectural Features

### 1. Dual-Engine Architecture (Cloud LLM + Local Fallback)
Vocalis AI remains fully operational even if external LLM services are unavailable. If `OPENROUTER_API_KEY` is missing or fails, the system automatically falls back to its built-in rule-based NLP engine, extracting action items and generating summaries using custom regular expression matching.

### 2. Native Tanglish & Bilingual Support
Meetings in regional corporate settings often feature code-switching (mixing English with Tamil). Vocalis AI detects Tamil script and Tanglish vocabulary tokens, automatically generating overall meeting summaries in natural Tanglish while preserving technical business terms.

### 3. Zero-Hallucination Task Grounding
Action items are strictly grounded in spoken transcript sentences. The system filters out opinions, forecasts, and conversational acknowledgements ("Sure", "Will do"), extracting only verbatim commitments and mapping them to the correct speaker.

---

## 5. File & Directory Structure

```
Meeting-summarize-main/
├── app.py                   # Main FastAPI Application & Backend Logic
├── requirements.txt         # Python Package Dependencies
├── render.yaml              # Render Deployment Blueprint Configuration
├── Procfile                 # Process Manager Directive for Web Host
├── start.sh                 # Startup Shell Script binding dynamic $PORT
├── index.html               # Landing Home Page UI
├── workspace.html           # Meeting Intelligence Workspace UI
├── style.css                # Custom Glassmorphic CSS Design System
├── script.js                # Client-side Async JavaScript Engine
├── static/                  # Static Asset Mirror Directory
│   ├── index.html
│   ├── workspace.html
│   ├── style.css
│   └── script.js
├── .env.example             # Template for Environment Variables
└── .gitignore               # Ignored Files & Directories
```

---
*Document Generated for Vocalis AI — Meeting Intelligence Platform.*
