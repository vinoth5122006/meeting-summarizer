from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import assemblyai as aai
import os
import shutil
import tempfile
import json
import requests
import re
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load .env file for local development (no-op in production)
load_dotenv()

app = FastAPI(title="Vocalis AI - Meeting Intelligence")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# Load AssemblyAI API Key from environment (set in Render dashboard or .env locally)
INBUILT_AAI_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
if INBUILT_AAI_KEY:
    aai.settings.api_key = INBUILT_AAI_KEY
else:
    print("WARNING: ASSEMBLYAI_API_KEY is not set. Transcription will not work until it is added.")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_file):
        index_file = os.path.join(BASE_DIR, "index.html")
    with open(index_file, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/workspace", response_class=HTMLResponse)
async def read_workspace():
    ws_file = os.path.join(STATIC_DIR, "workspace.html")
    if not os.path.exists(ws_file):
        ws_file = os.path.join(BASE_DIR, "workspace.html")
    with open(ws_file, "r", encoding="utf-8") as f:
        return f.read()

def is_bilingual_or_tamil(text: str) -> bool:
    """Detect if input text contains Tamil script or common Tanglish words."""
    if re.search(r'[\u0B80-\u0BFF]', text):
        return True
    tanglish_words = {
        'naan', 'nanga', 'neenga', 'avanga', 'enna', 'edhu', 'epdi', 'eppadi',
        'romba', 'nalla', 'irukku', 'irukanga', 'pannunga', 'pannalam', 'panren',
        'panniten', 'solren', 'sollunga', 'sonnaru', 'kudunga', 'vaanga', 'ponga',
        'illai', 'illa', 'aama', 'appo', 'ippo', 'adhu', 'idhu', 'pathu', 'pathi',
        'kooda', 'mattum', 'mudiyum', 'mudiyathu', 'theva', 'venum', 'theriyum',
        'pesalam', 'pesunga', 'pannu', 'tharen', 'mudinjuthu', 'aachu',
        'panna', 'panrom', 'pannom', 'panunga', 'sollu', 'kelunga', 'parkurom',
        'mudikanum', 'mudikkanum', 'anupunga', 'anupuren'
    }
    tokens = set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))
    return len(tokens.intersection(tanglish_words)) >= 1

# ── Compiled patterns used for built-in action extraction ────────────────────

# Concrete action verbs that explicitly indicate something must be done
CONCRETE_ACTION_RE = re.compile(
    r'\b(upload|send|share|submit|create|prepare|update|check|verify|fix|deploy|complete|'
    r'finish|schedule|mail|email|write|draft|organize|test|implement|add|build|develop|'
    r'collect|gather|coordinate|confirm|integrate|migrate|move|publish|release|'
    r'remove|replace|set\s*up|push|pull|merge|commit|raise|assign|hand\s*over|hand\s*off|'
    r'get|bring|deliver|install|configure|run|execute|connect|open|close|approve|'
    r'book|arrange|clarify|document|log|track|call|contact|inform|notify|reach\s*out|'
    r'follow\s*up|report|present|demo|demonstrate|export|import|backup|generate|'
    r'make\s*sure|ensure|review\s+the|fix\s+the|send\s+the|share\s+the|upload\s+the)\b',
    re.IGNORECASE
)

# Modal triggers — valid as action triggers ONLY when sentence has concrete object (6+ words)
MODAL_TASK_RE = re.compile(
    r'\b(i\s+will|i\'ll|i\'m\s+going\s+to|i\s+need\s+to|i\s+have\s+to|i\s+must|'
    r'can\s+you|could\s+you|please|kindly|you\s+need\s+to|you\s+should|'
    r'we\s+need\s+to|we\s+should|we\s+must|we\s+have\s+to|let\'s|let\s+us)\b',
    re.IGNORECASE
)

# Tanglish action patterns
TANGLISH_ACTION_RE = re.compile(
    r'\b(upload\s*pannu|upload\s*pannunga|share\s*pannu|share\s*pannunga|'
    r'send\s*pannu|send\s*pannunga|anupunga|anupu|anupuren|'
    r'check\s*pannu|check\s*pannunga|prepare\s*pannu|prepare\s*pannunga|'
    r'complete\s*pannu|complete\s*pannunga|fix\s*pannu|fix\s*pannunga|'
    r'create\s*pannu|create\s*pannunga|update\s*pannu|update\s*pannunga|'
    r'verify\s*pannu|verify\s*pannunga|test\s*pannu|test\s*pannunga|'
    r'schedule\s*pannu|schedule\s*pannunga|implement\s*pannu|implement\s*pannunga|'
    r'deploy\s*pannu|deploy\s*pannunga|generate\s*pannu|generate\s*pannunga|'
    r'setup\s*pannu|setup\s*pannunga|configure\s*pannu|configure\s*pannunga|'
    r'mail\s*pannu|mail\s*pannunga|email\s*pannu|email\s*pannunga|'
    r'panna\s*venum|pannanum|panna\s*porom|panna\s*irukkom|panren|mudikanum|mudikkanum)\b',
    re.IGNORECASE
)

# Noise filter: opinions, observations, compliments, forecasts — NOT tasks
NOISE_RE = re.compile(
    r'\b(i\s+think|i\s+believe|i\s+feel|i\s+hope|i\s+guess|i\s+assume|'
    r'probably|maybe|perhaps|it\s+seems|it\s+appears|'
    r'it\s+will\s+be|it\s+should\s+be|it\s+would\s+be|it\s+could\s+be|it\s+might\s+be|'
    r'things\s+will|team\s+will\s+be|project\s+will|this\s+will\s+be|that\s+will\s+be|'
    r'should\s+be\s+fine|will\s+be\s+fine|should\s+be\s+okay|will\s+be\s+okay|'
    r'will\s+be\s+good|looks\s+good|sounds\s+good|seems\s+good|great\s+job|'
    r'good\s+work|nice\s+work|well\s+done|that\'s\s+fine|that\s+is\s+fine|'
    r'it\'s\s+fine|no\s+problem|of\s+course|absolutely|definitely|certainly|for\s+sure|'
    r'i\s+agree|agreed|that\'s\s+correct|that\s+is\s+correct)\b',
    re.IGNORECASE
)

# Short acknowledgement-only sentences to skip even if they match a pattern
ACKNOWLEDGEMENT_RE = re.compile(
    r'^(sure|yes|yeah|yep|ok|okay|alright|right|got\s+it|noted|understood|'
    r'will\s+do|definitely|absolutely|of\s+course|no\s+problem|sounds\s+good|'
    r'look\s+into\s+it|i\'ll\s+check|i\'ll\s+do\s+it|panren|aachu|seri)[.!?,\s]*$',
    re.IGNORECASE
)

def extract_action_items(speaker_data: Dict[str, List[str]], all_speakers: List[str]) -> List[Dict[str, str]]:
    """
    Extract ONLY explicitly mentioned action items from the transcript.
    Returns tasks with exact wording, who raised them, and who they are assigned to.
    """
    action_items: List[Dict[str, str]] = []
    seen_tasks: set = set()

    for spk, texts in speaker_data.items():
        full_text = " ".join(texts)
        # Split on sentence-ending punctuation
        raw_sentences = re.split(r'(?<=[.?!])\s+', full_text)
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        for s in sentences:
            s_clean = s.strip()
            s_lower = s_clean.lower()
            word_count = len(s_clean.split())

            # ── Pre-filters ───────────────────────────────────────────────
            # Skip one-word or very short sentences
            if word_count < 4:
                continue

            # Skip pure acknowledgement phrases like "Sure.", "Noted.", "Will do.", "Panren."
            if ACKNOWLEDGEMENT_RE.match(s_clean):
                continue

            # Skip opinion/observation sentences (noise)
            if NOISE_RE.search(s_lower):
                continue

            # ── Check if sentence contains an actionable trigger ──────────
            has_concrete = CONCRETE_ACTION_RE.search(s_clean)
            has_tanglish = TANGLISH_ACTION_RE.search(s_clean)
            has_modal = MODAL_TASK_RE.search(s_clean) and word_count >= 6

            if not (has_concrete or has_tanglish or has_modal):
                continue

            # ── Determine who is assigned ─────────────────────────────────
            # Self-commitment patterns
            if re.search(
                r'\b(i\s+will|i\'ll|i\s+am\s+going\s+to|i\'m\s+going\s+to|'
                r'i\s+need\s+to|i\s+have\s+to|i\s+can\s+handle|panren|anupuren)\b',
                s_lower
            ):
                assigned = spk
            else:
                found_target = False
                for other_spk in all_speakers:
                    if other_spk.lower() in s_lower:
                        assigned = other_spk
                        found_target = True
                        break

                if not found_target:
                    if re.search(
                        r'\b(can\s+you|could\s+you|please|kindly|'
                        r'you\s+need\s+to|you\s+should|you\s+will|pannunga|anupunga)\b',
                        s_lower
                    ):
                        other_speakers = [sn for sn in all_speakers if sn != spk]
                        assigned = other_speakers[0] if other_speakers else "Assigned Participant"
                    elif re.search(
                        r'\b(we\s+will|we\'ll|we\s+need\s+to|we\s+should|let\'s|let\s+us|team)\b',
                        s_lower
                    ):
                        assigned = "Entire Team"
                    else:
                        assigned = spk

            # ── Clean task text while preserving exact words ──────────────
            task_text = re.sub(
                r'^(and|so|also|then|well|yeah|okay|ok|sure|right|alright|yes|no)\s+',
                '', s_clean, flags=re.IGNORECASE
            ).strip()
            if not task_text:
                continue
            task_text = task_text[0].upper() + task_text[1:]

            task_key = task_text.lower()[:60]
            if task_key not in seen_tasks and len(action_items) < 12:
                seen_tasks.add(task_key)
                action_items.append({
                    "task": task_text,
                    "raised_by": spk,
                    "assigned_to": assigned
                })

    return action_items


def call_openrouter_api(api_key: str, formatted_text: str) -> str:
    prompt = f"""
You are an executive meeting analyst and corporate transcription expert.

CRITICAL BILINGUAL / TANGLISH RULE FOR OVERALL SUMMARY:
- Analyze the input transcript to determine if the discussion is bilingual (mix of Tamil & English, or Tanglish) or pure English.
- IF THE INPUT IS BILINGUAL OR CONTAINS TAMIL/TANGLISH:
  The "overall_summary" MUST BE WRITTEN IN NATURAL TANGLISH (Tamil language transliterated in English/Latin letters, retaining English technical and business terms naturally, e.g., "Intha meeting-la participants project progress, key milestones, and timeline pathi detailed-ah discuss pannanga...").
- IF THE INPUT IS PURE ENGLISH:
  The "overall_summary" must be in professional English.

Task:
1. "overall_summary": Provide ONE comprehensive overall meeting summary following the language rule above.
2. "personwise_summary": Generate detailed person-wise summaries for each speaker. List every speaker separately and summarize their statements, proposals, arguments, and contributions.
3. "action_items": Extract all actionable tasks, work items, and commitments discussed in the meeting.
   CRITICAL GROUNDING RULE FOR ACTIONS:
   - ONLY include work/tasks that are ACTUALLY AND EXPLICITLY mentioned in the input transcript.
   - ABSOLUTELY DO NOT invent, assume, paraphrase, or add any actions of your own that are not word-for-word stated in the transcript.
   - DO NOT generate actions like "review meeting notes", "distribute summary", or "prepare for next meeting" unless a speaker literally said those exact words.
   - If no explicit tasks were mentioned in the meeting, return an empty array [] for "action_items".
   - For each genuine task mentioned:
     - "task": Copy the EXACT verbatim words/phrase spoken by the speaker from the transcript — do NOT rewrite, paraphrase, or summarize. Use the speaker's own words as-is (e.g., if the speaker said "upload the resource files by tomorrow", the task must be exactly "upload the resource files by tomorrow").
     - "raised_by": Who said or requested the work (e.g. "Speaker A").
     - "assigned_to": Who the work is assigned to (e.g. "Speaker B", or "Speaker A" if self-assigned).

Format your output purely as a JSON object:
{{
  "overall_summary": "...",
  "personwise_summary": [
    {{ "speaker": "Speaker A", "summary": "..." }},
    {{ "speaker": "Speaker B", "summary": "..." }}
  ],
  "action_items": [
    {{
      "task": "...",
      "raised_by": "Speaker A",
      "assigned_to": "Speaker B"
    }}
  ]
}}

Transcript:
{formatted_text}
"""
    clean_api_key = api_key.strip().encode('ascii', 'ignore').decode('ascii')
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {clean_api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }
    data = {
        "model": "openai/gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post(url, headers=headers, data=json.dumps(data, ensure_ascii=False).encode('utf-8'), timeout=60)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']


def generate_builtin_analysis(transcript: Any, formatted_text: str) -> Dict[str, Any]:
    """Fallback built-in analysis: overall summary (Tanglish if bilingual), person-wise summary, action items."""
    speaker_data: Dict[str, List[str]] = {}
    utterance_list = getattr(transcript, 'utterances', None) or []

    if utterance_list:
        for u in utterance_list:
            spk = f"Speaker {u.speaker}" if u.speaker else "Speaker A"
            if spk not in speaker_data:
                speaker_data[spk] = []
            if u.text and u.text.strip():
                speaker_data[spk].append(u.text.strip())
    else:
        raw = getattr(transcript, 'text', '') or formatted_text or ''
        speaker_data["Speaker A"] = [raw.strip()] if raw.strip() else []

    all_speakers = list(speaker_data.keys())

    # 1. Person-wise Summary
    personwise_summary = []
    for spk, texts in speaker_data.items():
        combined = " ".join(texts)
        if len(combined) > 350:
            sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+', combined) if s.strip()]
            summary_sentences = sentences[:3] + ([sentences[-1]] if len(sentences) > 3 else [])
            summary_text = " ".join(summary_sentences)
        else:
            summary_text = combined if combined else "Contributed observations and feedback during the meeting."
        personwise_summary.append({"speaker": spk, "summary": summary_text})

    # 2. Action Items — extracted using improved built-in engine
    action_items = extract_action_items(speaker_data, all_speakers)
    # Note: action_items may be [] if nothing was explicitly mentioned. No placeholders added.

    # 3. Overall Meeting Summary (Tanglish if bilingual, English otherwise)
    total_speakers = len(speaker_data)
    total_words = len(formatted_text.split())
    bilingual_detected = is_bilingual_or_tamil(formatted_text)

    if bilingual_detected:
        summary_parts = [
            f"Intha meeting-la total-ah {total_speakers} participants join panni key topics and project updates pathi detailed-ah discuss pannanga (approx {total_words} words)."
        ]
        for spk, texts in speaker_data.items():
            if texts:
                summary_parts.append(
                    f"{spk} primary updates and key discussion points share pannaru: '{texts[0][:120]}...'."
                )
        summary_parts.append(
            "Elloarum key points pathi discuss panni mudivu eduthu, respective action items assign pannirukanga. Next steps and execution plan finalise aagirukku."
        )
        overall_summary = " ".join(summary_parts)
    else:
        summary_parts = [
            f"The meeting brought together {total_speakers} participant{'s' if total_speakers != 1 else ''} "
            f"for an in-depth operational discussion spanning approximately {total_words} words."
        ]
        for spk, texts in speaker_data.items():
            if texts:
                summary_parts.append(
                    f"{spk} highlighted primary discussion points regarding project milestones and deliverables."
                )
        summary_parts.append(
            "Participants concluded with defined action items and mutual alignment on subsequent steps."
        )
        overall_summary = " ".join(summary_parts)

    return {
        "overall_summary": overall_summary,
        "personwise_summary": personwise_summary,
        "action_items": action_items,
        "is_bilingual": bilingual_detected
    }


@app.post("/api/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    openrouter_key: Optional[str] = Form(None)
):
    try:
        if not INBUILT_AAI_KEY:
            raise HTTPException(status_code=503, detail="ASSEMBLYAI_API_KEY is not configured on the server. Please add it in the Render environment variables.")

        suffix = os.path.splitext(file.filename)[1] if file.filename else ".mp3"
        if not suffix:
            suffix = ".mp3"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        config = aai.TranscriptionConfig(speaker_labels=True, speech_models=["universal"])
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(tmp_path, config)

        try:
            os.unlink(tmp_path)
        except Exception:
            pass

        if transcript.status == aai.TranscriptStatus.error:
            raise HTTPException(status_code=500, detail=f"AssemblyAI Transcription Error: {transcript.error}")

        formatted_text = ""
        utterance_details = []
        if transcript.utterances:
            for utterance in transcript.utterances:
                spk = f"Speaker {utterance.speaker}"
                formatted_text += f"{spk}: {utterance.text}\n"
                utterance_details.append({
                    "speaker": spk,
                    "text": utterance.text,
                    "start": utterance.start,
                    "end": utterance.end
                })
        else:
            formatted_text = transcript.text or ""
            utterance_details.append({
                "speaker": "Speaker A",
                "text": transcript.text or "",
                "start": 0,
                "end": 0
            })

        effective_or_key = openrouter_key or os.getenv("OPENROUTER_API_KEY")
        analysis_data = None
        bilingual_detected = is_bilingual_or_tamil(formatted_text)

        if effective_or_key and effective_or_key.strip():
            try:
                summary_text = call_openrouter_api(effective_or_key, formatted_text)
                cleaned_text = summary_text.strip()
                if cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text.split("\n", 1)[-1]
                    if cleaned_text.endswith("```"):
                        cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()
                parsed_data = json.loads(cleaned_text)

                raw_actions = parsed_data.get("action_items", [])
                formatted_actions = []
                for act in raw_actions:
                    if isinstance(act, dict):
                        formatted_actions.append({
                            "task": act.get("task", ""),
                            "raised_by": act.get("raised_by", "Speaker Unknown"),
                            "assigned_to": act.get("assigned_to", "Team")
                        })
                    else:
                        formatted_actions.append({
                            "task": str(act),
                            "raised_by": "Meeting Lead",
                            "assigned_to": "Action Owner"
                        })

                raw_personwise = parsed_data.get("personwise_summary") or parsed_data.get("speaker_points", [])
                formatted_personwise = []
                for p in raw_personwise:
                    if isinstance(p, dict):
                        formatted_personwise.append({
                            "speaker": p.get("speaker", "Speaker"),
                            "summary": p.get("summary") or p.get("text", "")
                        })

                analysis_data = {
                    "overall_summary": parsed_data.get("overall_summary", ""),
                    "personwise_summary": formatted_personwise,
                    "action_items": formatted_actions,
                    "is_bilingual": bilingual_detected
                }
            except Exception as llm_err:
                print(f"External LLM generation fallback: {llm_err}")

        # Fallback to built-in analysis
        if not analysis_data or not analysis_data.get("overall_summary"):
            analysis_data = generate_builtin_analysis(transcript, formatted_text)

        return {
            "status": "success",
            "raw_transcript": formatted_text,
            "overall_summary": analysis_data.get("overall_summary", ""),
            "personwise_summary": analysis_data.get("personwise_summary", []),
            "action_items": analysis_data.get("action_items", []),
            "is_bilingual": analysis_data.get("is_bilingual", bilingual_detected),
            "utterances": utterance_details
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
