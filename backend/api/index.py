# main.py
import io
import json
import re
from typing import Dict, List, Any

from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

import pdfplumber
import docx

import fitz  # PyMuPDF
from groq import Groq
import os
from groq import Groq
from dotenv import load_dotenv

# Load .env file (optional, useful for local dev)
load_dotenv()

# ---------- CONFIG ----------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not set. Please add it to your environment or .env file.")

client = Groq(api_key=GROQ_API_KEY)

app = FastAPI(title="Intelligent Resume Enhancer")
origins = [
    "https://ats-u3wf.vercel.app",  # your frontend
    "http://localhost:5173"         # for local dev (Vite)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Helpers: extraction ----------
def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for p in pdf.pages:
                t = p.extract_text()
                if t:
                    text += t + "\n"
    except Exception:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for p in doc:
                text += p.get_text("text") + "\n"
        except Exception:
            return ""
    return text.strip()

def extract_text_from_docx_bytes(file_bytes: bytes) -> str:
    try:
        d = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in d.paragraphs).strip()
    except Exception:
        return ""




# ---------- Utilities: sanitizers ----------
def extract_first_json_object(s: str) -> str:
    if not s or "{" not in s:
        return ""
    start = s.find("{")
    depth = 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    return ""

def extract_first_json_array(s: str) -> str:
    if not s or "[" not in s:
        return ""
    start = s.find("[")
    depth = 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    return ""

def sanitize_rewritten_text(raw: str, fallback: str = "") -> str:
    if not raw:
        return fallback or ""
    s = raw.strip()
    # Remove code fences
    s = re.sub(r"^```[a-zA-Z]*\n", "", s)
    s = re.sub(r"\n```$", "", s)
    # If full JSON object, attempt to extract enhanced_text field
    try:
        if s.startswith("{") and s.endswith("}"):
            parsed = json.loads(s)
            if isinstance(parsed, dict) and parsed.get("enhanced_text"):
                s = parsed["enhanced_text"]
            else:
                s = ""
    except Exception:
        pass
    # Remove trailing appended JSON object if present
    last_open = s.rfind("{")
    last_close = s.rfind("}")
    if last_open != -1 and last_close != -1 and last_close > last_open:
        maybe = s[last_open:last_close+1]
        try:
            _ = json.loads(maybe)
            s = s[:last_open].strip()
        except Exception:
            pass
    s = s.replace("```", "")
    s = re.sub(r"\n{2,}", "\n\n", s).strip()
    # try to decode escapes
    try:
        decoded = bytes(s, "utf-8").decode("unicode_escape")
        if isinstance(decoded, str) and len(decoded) >= max(10, len(s) - 5):
            s = decoded
    except Exception:
        pass
    s = s.strip()
    return s if s else (fallback or "")

# ---------- LLM wrappers ----------
def ask_groq_for_analysis(resume_text: str, job_description: str) -> Dict[str, Any]:
    prompt = f"""
You are an expert resume/ATS coach. Compare the resume and the job description.
Return a JSON object ONLY (no Markdown, no explanation) with keys:
- original_score: float (0-10)
- final_score: float (0-10)
- changes_made: array of objects with fields "change", "reason", "ats_impact"
- enhanced_text: the FULL rewritten resume text (plain text)
- overall_explanation: include what changes and suggestions you have in atleast 2-3 lines for each change , how its relevant to our resume and keywords if user gave and its 
   impact on resume and give most relevant points.
- Give atleast 5 strong points.
- Provide a **very detailed analysis** with these sections:

1. **Strengths** – highlight good points
2. **Weaknesses** – what’s missing or weak
3. **Suggestions** – concrete improvements
4. **ATS Analysis** – how ATS may score it, keyword matches, formatting issues
Job Description:
{job_description}

Resume:
{resume_text}
"""
    try:
        completion = client.chat.completions.create(
            model="gemma2-9b-it",
            messages=[
                {"role": "system", "content": "You are an ATS scoring + rewriting engine. Output JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_completion_tokens=2500,
        )
        raw = completion.choices[0].message.content.strip()
    except Exception as e:
        return {"error": f"LLM request failed: {e}"}

    json_sub = extract_first_json_object(raw)
    parsed = None
    if json_sub:
        try:
            parsed = json.loads(json_sub)
        except Exception:
            parsed = None

    if not parsed:
        try:
            parsed = json.loads(raw)
        except Exception:
            # fallback: put raw into enhanced_text
            parsed = {
                "original_score": None,
                "final_score": None,
                "changes_made": [],
                "enhanced_text": raw,
                "overall_explanation": "LLM returned non-JSON; raw output placed into enhanced_text"
            }

    # sanitize enhanced_text
    parsed["enhanced_text"] = sanitize_rewritten_text(parsed.get("enhanced_text", ""), fallback=parsed.get("overall_explanation", ""))
    if parsed.get("original_score") is None:
        parsed["original_score"] = 0.0
    if parsed.get("final_score") is None:
        parsed["final_score"] = parsed["original_score"]

    return parsed

def rewrite_resume_strict(resume_text: str, job_description: str) -> str:
    system_msg = (
        "You are a resume rewriting assistant. Output ONLY the rewritten resume text - "
        "no JSON, no markdown, no code fences, and no explanations."
    )
    user_prompt = f"""
Original Resume (plain text):
{resume_text}

Job Description / Keywords:
{job_description}

Task:
Rewrite the ENTIRE resume to be clearer, more impactful, and more ATS-friendly.
Preserve section headings (EDUCATION, EXPERIENCE, SKILLS, PROJECTS).
Return ONLY the rewritten resume text (plain text).
"""
    try:
        completion = client.chat.completions.create(
            model="gemma2-9b-it",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.25,
            max_completion_tokens=1400,
        )
        raw = completion.choices[0].message.content.strip()
    except Exception as e:
        print("LLM rewrite failed:", e)
        return resume_text
    cleaned = sanitize_rewritten_text(raw, fallback=resume_text)
    return cleaned

def get_changes_from_enhanced(original_resume: str, enhanced_text: str, job_description: str) -> List[Dict[str, str]]:
    """
    Fallback: ask LLM to return a short JSON array of changes (change, reason, ats_impact).
    We give it the original resume and the enhanced text to base the changes on.
    """
    prompt = f"""
You are an expert resume editor. Produce a JSON array ONLY describing the specific changes applied or recommended.
Each array element should be an object with keys:
- change: a short title of the change
- reason: why you did it and what impact it will have in 2-3 lines for each change .
- ats_impact: one-word or short phrase (Positive/Neutral/Negative)

Use the ORIGINAL resume and the ENHANCED resume below to list the changes that were made or should be made.
Return most relevant and impactful changes. You will also have job keyword if provided for more specific resume or you yourslef presume from resume content.

Job Description: {job_description}

ORIGINAL RESUME:
{original_resume}

ENHANCED RESUME:
{enhanced_text}
"""
    try:
        completion = client.chat.completions.create(
            model="gemma2-9b-it",
            messages=[{"role": "system", "content": "You are a concise resume change summarizer. Output JSON array only."},
                      {"role": "user", "content": prompt}],
            temperature=0.15,
            max_completion_tokens=700,
        )
        raw = completion.choices[0].message.content.strip()
    except Exception as e:
        print("get_changes_from_enhanced failed:", e)
        return []

    json_arr = extract_first_json_array(raw)
    if json_arr:
        try:
            parsed = json.loads(json_arr)
            # normalize entries
            normalized = []
            for it in parsed:
                if isinstance(it, dict):
                    normalized.append({
                        "change": str(it.get("change", "")).strip(),
                        "reason": str(it.get("reason", "")).strip(),
                        "ats_impact": str(it.get("ats_impact", "")).strip(),
                    })
            return normalized
        except Exception:
            pass
    # Last resort: return empty
    return []

# ---------- Summarize for UI ----------


# ---------- PDF rebuild (keeps images/logos) ----------
def rebuild_pdf_with_text(original_pdf_bytes: bytes, enhanced_text: str) -> bytes:
    doc = fitz.open(stream=original_pdf_bytes, filetype="pdf")
    for page in doc:
        try:
            blocks = page.get_text("blocks")
        except Exception:
            blocks = []
        for b in blocks:
            if len(b) >= 5 and isinstance(b[4], str) and b[4].strip():
                bbox = fitz.Rect(b[:4])
                expand = 0.3
                bbox = fitz.Rect(bbox.x0 - expand, bbox.y0 - expand, bbox.x1 + expand, bbox.y1 + expand)
                page.draw_rect(bbox, color=(1,1,1), fill=(1,1,1))

    words = enhanced_text.split()
    if not words:
        return original_pdf_bytes

    fontname = "helv"
    fontsize = 11
    line_height = fontsize + 4
    left_margin = 72
    right_margin = 72
    top_margin = 80
    bottom_margin = 72

    page_index = 0
    page = doc[page_index]
    usable_width = page.rect.width - left_margin - right_margin
    y = top_margin
    current_line = ""
    i = 0

    def width_of(line, p):
        try:
            return p.get_text_length(line, fontsize=fontsize, fontname=fontname)
        except Exception:
            return len(line) * (fontsize * 0.55)

    while i < len(words):
        w = words[i]
        candidate = (current_line + " " + w).strip() if current_line else w
        if width_of(candidate, page) <= usable_width:
            current_line = candidate
            i += 1
        else:
            if current_line.strip():
                page.insert_text((left_margin, y), current_line, fontsize=fontsize, fontname=fontname, fill=(0,0,0))
                y += line_height
            current_line = ""
            if y > page.rect.height - bottom_margin:
                page_index += 1
                if page_index >= len(doc):
                    doc.new_page()
                page = doc[page_index]
                usable_width = page.rect.width - left_margin - right_margin
                y = top_margin

    if current_line.strip():
        page.insert_text((left_margin, y), current_line, fontsize=fontsize, fontname=fontname, fill=(0,0,0))
        y += line_height

    out = io.BytesIO()
    doc.save(out, deflate=True)
    return out.getvalue()

# ---------- Routes ----------


@app.post("/analyze")
async def analyze_route(
    file: UploadFile,
    job_description: str = Form(""),
    keywords: str = Form("[]")
):
    file_bytes = await file.read()
    ext = file.filename.split(".")[-1].lower()

    # parse keywords list
    try:
        keywords_list: List[str] = json.loads(keywords)
        if not isinstance(keywords_list, list):
            keywords_list = []
    except Exception:
        keywords_list = []

    # Extract resume text
    if ext == "pdf":
        resume_text = extract_text_from_pdf_bytes(file_bytes)
    elif ext in ("docx", "doc"):
        resume_text = extract_text_from_docx_bytes(file_bytes)
    elif ext in ("png", "jpg", "jpeg"):
        return JSONResponse({"error": "Image files are not supported. Please upload PDF or DOCX."}, status_code=400)
    else:
        return JSONResponse({"error": "Unsupported file type"}, status_code=400)

    if not resume_text:
        return JSONResponse({"error": "Could not extract text from the file."}, status_code=400)

    # merge JD + keywords
    jd_plus_kw = job_description + ("\n\nExtra Keywords: " + ", ".join(keywords_list) if keywords_list else "")

    parsed = ask_groq_for_analysis(resume_text, jd_plus_kw)
    if parsed.get("error"):
        parsed = {
            "original_score": None,
            "final_score": None,
            "changes_made": [],
            "enhanced_text": rewrite_resume_strict(resume_text, jd_plus_kw),
            "overall_explanation": "LLM analysis failed; provided enhanced text via strict rewrite."
        }

    summary = summarize_for_ui(parsed, resume_text, jd_plus_kw)
    return JSONResponse(summary)


@app.post("/enhance")
async def enhance_route(
    file: UploadFile,
    job_description: str = Form(""),
    keywords: str = Form("[]")
):
    file_bytes = await file.read()
    if file.filename.split(".")[-1].lower() != "pdf":
        return JSONResponse({"error": "Only PDF supported for /enhance"}, status_code=400)

    # parse keywords
    try:
        keywords_list: List[str] = json.loads(keywords)
        if not isinstance(keywords_list, list):
            keywords_list = []
    except Exception:
        keywords_list = []

    resume_text = extract_text_from_pdf_bytes(file_bytes)
    if not resume_text:
        return JSONResponse({"error": "Could not extract text from PDF"}, status_code=400)

    jd_plus_kw = job_description + ("\n\nExtra Keywords: " + ", ".join(keywords_list) if keywords_list else "")

    # rewrite
    enhanced_text = rewrite_resume_strict(resume_text, jd_plus_kw)
    if not enhanced_text or len(enhanced_text.strip()) < 10:
        enhanced_text = resume_text

    new_pdf = rebuild_pdf_with_text(original_pdf_bytes=file_bytes, enhanced_text=enhanced_text)
    return StreamingResponse(
        io.BytesIO(new_pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=enhanced_{file.filename}"}
    )
import math
import re

# Simple heuristic fallback ATS scoring (if LLM does not provide scores)
def heuristic_scores(text: str) -> float:
    """
    Returns a single heuristic ATS-like score in 0-10 range.
    You can tune this logic; it's a simple fallback if LLM doesn't return scores.
    """
    if not text or len(text.strip()) < 30:
        return 3.0
    edu = 5 if re.search(r"(degree|university|bachelor|master|phd)", text, re.I) else 3
    skills = min(10, len(re.findall(r"\b(python|java|c\+\+|sql|react|ml|ai|tensorflow|pytorch)\b", text, re.I)))
    exp = 5 if re.search(r"(experience|worked at|project|internship|company)", text, re.I) else 3
    final = round((edu + skills + exp) / 3, 1)
    # clamp 0..10
    return max(0.0, min(10.0, float(final)))

# Update summarize_for_ui to use heuristics if needed and compute improvement percentage
def summarize_for_ui(parsed: dict, original_resume_text: str, job_description: str) -> dict:
    # get scores from LLM if present
    orig = parsed.get("original_score")
    final = parsed.get("final_score")

    # If LLM did not return numeric scores, compute fallback heuristics
    if orig is None:
        orig = heuristic_scores(original_resume_text)
    else:
        try:
            orig = float(orig)
        except Exception:
            orig = heuristic_scores(original_resume_text)

    if final is None:
        # If LLM did not return final_score, use heuristic on enhanced_text if exists, else increase a bit
        enhanced_text = parsed.get("enhanced_text", "")
        if enhanced_text and len(enhanced_text.strip()) > 20:
            final = heuristic_scores(enhanced_text)
        else:
            # small bump to indicate potential improvement
            final = min(10.0, orig + 1.0)
    else:
        try:
            final = float(final)
        except Exception:
            final = heuristic_scores(parsed.get("enhanced_text", "") or original_resume_text)

    # compute improvement percentage (relative to original)
    try:
        improvement_percentage = round(((final - orig) / max(orig, 1e-6)) * 100, 1)
    except Exception:
        improvement_percentage = 0.0

    # overview and detailed changes logic (reuse your existing normalization)
    overview = parsed.get("overall_explanation") or ""
    raw_changes = parsed.get("changes_made") or []
    detailed = []
    if raw_changes and isinstance(raw_changes, list):
        for item in raw_changes:
            if isinstance(item, dict):
                detailed.append({
                    "change": item.get("change", "").strip(),
                    "reason": item.get("reason", "").strip(),
                    "ats_impact": item.get("ats_impact", "").strip() or item.get("impact", "").strip()
                })
    # fallback: optionally the caller may already populate detailed via fallback LLM call
    if not overview:
        if detailed:
            top = [d["change"] for d in detailed[:3] if d.get("change")]
            overview = "Top suggestions: " + "; ".join(top) if top else "No major suggestions."

    enhanced_text_preview = parsed.get("enhanced_text") or ""
    # sanitize (basic)
    if isinstance(enhanced_text_preview, str):
        enhanced_text_preview = re.sub(r"```[a-zA-Z]*", "", enhanced_text_preview).replace("```", "").strip()

    preview = "\n".join([ln.strip() for ln in enhanced_text_preview.splitlines() if ln.strip()])[:2000]
    if len(enhanced_text_preview) > 2000:
        preview = preview.rstrip() + "\n\n(...truncated preview...)"

    return {
        "original_score": round(orig, 1),
        "final_score": round(final, 1),
        "improvement_percentage": improvement_percentage,
        "overview": overview,
        "detailed_changes": detailed,
        "enhanced_text_preview": preview,
    }
from fastapi import Request
from fastapi.responses import JSONResponse

@app.middleware("http")
async def limit_request_body(request: Request, call_next):
    max_bytes = 5 * 1024 * 1024  # 5MB
    if request.headers.get("content-length") and int(request.headers["content-length"]) > max_bytes:
        return JSONResponse({"error": "File too large (max 5MB)"}, status_code=413)
    return await call_next(request)



from mangum import Mangum

# This is required so Vercel’s serverless runtime can call FastAPI
handler = Mangum.App(app)
