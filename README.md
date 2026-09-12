# Vocalis AI — Meeting Intelligence

> Turn meeting recordings into structured executive summaries instantly.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

---

## Features

- 🎙️ **Audio Transcription** — Powered by AssemblyAI with speaker diarization
- 📝 **Overall Meeting Summary** — Comprehensive executive takeaways
- 👥 **Person-wise Summary** — Individual speaker contributions
- ✅ **Action Items** — Who said what and who it's assigned to
- 🌐 **Bilingual Support** — English & Tamil/Tanglish detection

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI |
| Server | Uvicorn (ASGI) |
| Frontend | HTML + CSS + JavaScript |
| Transcription | AssemblyAI |
| Summarization | OpenRouter / GPT-4o-mini |

---

## Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/vinoth5122006/meeting-summarizer.git
cd meeting-summarizer

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
copy .env.example .env
# Edit .env and add your API keys

# 5. Run the app
uvicorn app:app --reload
# Open http://127.0.0.1:8000
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `ASSEMBLYAI_API_KEY` | Your AssemblyAI API key (required) |
| `OPENROUTER_API_KEY` | Your OpenRouter API key (optional — enables GPT-4o-mini summaries) |

---

## Deploying to Render

1. Fork or push this repo to your GitHub
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect this GitHub repository
4. Render auto-detects `render.yaml` — no manual config needed
5. Add your environment variables in the Render dashboard
6. Click **Deploy**

**Auto-deploy**: Every `git push` to `main` automatically updates the live app.

---

## Project Structure

```
meeting-summarizer/
├── app.py              # FastAPI backend
├── static/
│   ├── index.html      # Landing page
│   ├── workspace.html  # AI workspace
│   ├── script.js       # Frontend logic
│   └── style.css       # Styling
├── Procfile            # Render start command
├── render.yaml         # Render deployment config
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── .gitignore
```

---

© 2026 Vocalis AI. Enterprise-grade meeting transcription & analysis.
