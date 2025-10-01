
# -> frontend deployed on vercel : https://ats-u3wf.vercel.app/
# -> backend deployed at render :

some working images : <img width="1693" height="960" alt="Screenshot 2025-10-01 122158" src="https://github.com/user-attachments/assets/352fa884-f3df-4fe9-a803-cef5c49f2feb" />
<img width="1670" height="937" alt="Screenshot 2025-10-01 122149" src="https://github.com/user-attachments/assets/bb9ca59f-85de-450c-8492-dc5debe9c072" />
<img width="1670" height="937" alt="Screenshot 2025-10-01 122149" src="https://github.com/user-attachments/assets/3cc1032a-62f3-4a18-a6be-f861c923e636" />
<img width="1693" height="960" alt="Screenshot 2025-10-01 122158" src="https://github.com/user-attachments/assets/a4f90330-3559-490a-af84-6ae95b4cf60b" />


# 📄 Resume Analyzer Backend

A FastAPI-based backend that:
- Extracts text from resumes (PDF, DOCX)
- Analyzes content with **Groq LLM API**
- Rewrites resumes in a **strict, ATS-optimized format**
- Returns enhanced resume text and an optional rebuilt PDF

---

## ⚙️ Features
- **PDF / DOCX parsing** with `pdfplumber`, `fitz (PyMuPDF)`, and `python-docx`
- **LLM-powered analysis** (via Groq API)
- **Resume rewriting** into ATS-friendly format
- **Strict format mode** (section-based JSON → markdown table)
- **(Optional) OCR** support for image resumes (disabled by default for memory savings)

---

## 🛠️ Tech Stack
- **FastAPI** (API framework)
- **Groq API** (LLM inference)
- **pdfplumber + PyMuPDF** (PDF parsing & rebuilding)
- **python-docx** (DOCX parsing)
- **Uvicorn** (ASGI server)

---

## 🚀 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/resume-analyzer-backend.git
cd resume-analyzer-backend
2. Create & activate virtual environment
python3 -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows

3. Install dependencies
pip install -r requirements.txt

4. Add environment variables

Create a .env file in the project root:

GROQ_API_KEY=your_groq_api_key_here


Optional:

ENABLE_OCR=false   # keep disabled for Render free tier (saves memory)

5. Run locally
uvicorn main:app --reload --host 0.0.0.0 --port 8000


Visit 👉 http://localhost:8000/docs
 for interactive API docs.

📌 API Endpoints
POST /analyze_resume

Upload a resume (PDF or DOCX).
Returns extracted text + LLM-powered analysis.

POST /rewrite_resume

Upload a resume for ATS-friendly rewriting.

POST /rewrite_resume_strict

Upload a resume → returns JSON with:

ats_friendly_resume (markdown resume text)

job_recommendations (roles, skills, industries)
