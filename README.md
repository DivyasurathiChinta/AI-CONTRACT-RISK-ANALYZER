# 🤖 AI Contract Risk Analyzer

> A production-grade GenAI app that automatically extracts, classifies, and risk-scores legal contract clauses using Google Gemini AI, FastAPI, and Streamlit.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red.svg)](https://streamlit.io)
[![Gemini](https://img.shields.io/badge/Gemini-1.5_Flash-orange.svg)](https://ai.google.dev)

---

## 🎯 What It Does

| Step | Action | Technology |
|------|--------|------------|
| 1 | Upload PDF contract | Streamlit + FastAPI |
| 2 | Extract raw text | PyMuPDF |
| 3 | Clean & preprocess | Custom NLP pipeline |
| 4 | Extract & classify clauses | Gemini AI |
| 5 | Analyze risk per clause | Gemini + weighted scoring |
| 6 | Detect missing clauses | Gemini + checklist |
| 7 | Generate executive summary | Gemini structured output |
| 8 | Display visual report | Streamlit dashboard |

---

## 🏗 System Architecture

```
[Streamlit UI] ──HTTP──► [FastAPI Backend]
                               │
                    [ContractAnalyzer Pipeline]
                    ┌──────────┴──────────┐
             [PDF Extractor]    [Clause Extractor]
             [Risk Analyzer]    [Summary Generator]
                    └──────────┬──────────┘
                        [Gemini Service]
                               │
                        [Google Gemini API]
```

**Pipeline:** PDF → Extract Text → Clean → Extract Clauses → Analyze Risk → Detect Missing → Summarize → Return JSON

---

## 📁 Folder Structure

```
contract-risk-analyzer/
├── app/
│   ├── config.py          # Pydantic Settings (env var management)
│   └── main.py            # FastAPI entry point, CORS, lifespan
├── routers/
│   ├── upload.py          # POST /upload/
│   └── analysis.py        # POST /analyze/{file_id}
├── services/
│   ├── pdf_extractor.py   # PyMuPDF text extraction
│   ├── gemini_service.py  # Gemini API adapter (retry, JSON parse)
│   ├── clause_extractor.py
│   ├── risk_analyzer.py   # Weighted risk scoring engine
│   ├── summary_generator.py
│   └── contract_analyzer.py  # Main pipeline orchestrator
├── models/
│   └── contract.py        # All Pydantic schemas
├── prompts/
│   ├── clause_extraction.py
│   ├── risk_analysis.py
│   ├── missing_clauses.py
│   └── summary.py
├── utils/
│   ├── logger.py          # Loguru structured logging
│   ├── text_cleaner.py    # PDF noise removal pipeline
│   └── file_handler.py    # Secure upload + UUID naming
├── frontend/
│   └── streamlit_app.py   # Full Streamlit dashboard
├── tests/
│   ├── test_pdf_extractor.py
│   └── test_risk_analyzer.py
├── uploads/               # Temp PDF storage (auto-cleaned)
├── run.py                 # Dev startup script
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 🚀 Quick Start

### 1 — Setup Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2 — Configure Environment

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Edit `.env` and add your Gemini API key:
```env
GEMINI_API_KEY=your_actual_key_here
```
Get a free key at: https://aistudio.google.com/app/apikey

### 3 — Start Backend

```bash
python run.py
# API runs at:  http://localhost:8000
# Swagger docs: http://localhost:8000/docs
```

### 4 — Start Frontend (new terminal)

```bash
venv\Scripts\activate
streamlit run frontend/streamlit_app.py
# UI runs at: http://localhost:8501
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload/` | Upload a PDF contract |
| `POST` | `/analyze/{file_id}` | Run full AI analysis |
| `GET` | `/health` | Service health check |
| `GET` | `/docs` | Interactive Swagger UI |

---

## 🧪 Running Tests

```bash
pytest tests/ -v
pytest tests/ -v --cov=services --cov-report=term-missing
```

---

## 🚢 Deployment

### Streamlit Cloud (Frontend)
1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → Connect repo
3. Main file: `frontend/streamlit_app.py`
4. Add `GEMINI_API_KEY` in Secrets

### Render (Backend)
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Add env vars in Render dashboard

### Railway
```bash
npm install -g @railway/cli
railway login && railway init && railway up
```

---

## 🔮 Future Enhancements

- **RAG + Vector DB**: Pinecone/ChromaDB for clause similarity search
- **Multi-doc comparison**: Side-by-side contract diff
- **Redline suggestions**: AI-generated revised clause language
- **PostgreSQL**: Persist analysis history
- **Auth**: JWT-based user accounts
- **Batch processing**: Analyze multiple contracts at once

---

## 📄 License

MIT License — open for portfolio and learning use.
