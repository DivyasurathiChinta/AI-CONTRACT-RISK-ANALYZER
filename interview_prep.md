# 🎯 AI Contract Risk Analyzer — Interview Preparation Guide

---

## 📝 Resume Descriptions

### 2-Line Version
> Built an AI Contract Risk Analyzer using FastAPI, Google Gemini AI, and Streamlit that automatically extracts, classifies, and risk-scores legal contract clauses from PDF documents. Implemented a 5-stage async processing pipeline with structured prompt engineering, achieving clause extraction across 7 legal categories with risk scores and executive summaries.

### 5-Line Version
> Designed and developed a full-stack AI application that automates legal contract risk analysis using Google Gemini 1.5 Flash and a FastAPI backend. Built a 5-step async pipeline: PDF text extraction (PyMuPDF), NLP-based text cleaning, AI-powered clause classification (7 types), risk scoring with weighted algorithms (0–100 scale), and executive summary generation. Engineered structured Gemini prompts using role-prompting, few-shot examples, JSON schema enforcement, and explicit scoring rubrics to ensure consistent, calibrated AI output. Applied production-grade software patterns including the Adapter Pattern (Gemini service), Pipeline Pattern (analysis orchestrator), and Settings Pattern (Pydantic BaseSettings). Delivered a Streamlit dashboard with real-time risk visualization, clause cards, metric gauges, and downloadable JSON reports.

### LinkedIn Project Description
> **AI Contract Risk Analyzer** | Python · FastAPI · Google Gemini AI · Streamlit · PyMuPDF
>
> Built a production-ready GenAI application that automates legal contract analysis — a task that traditionally costs $300–$1000/hour in legal fees.
>
> **What it does:** Upload any PDF contract → AI extracts and classifies 7 clause types → assigns risk scores (0–100) → detects missing clauses → generates an executive summary in plain English.
>
> **Technical highlights:**
> - 5-stage async processing pipeline (Extract → Clean → Classify → Score → Summarize)
> - Structured prompt engineering with role-prompting, JSON schema enforcement, and scoring rubrics
> - Adapter Pattern wrapping Gemini API with retry logic and fault-tolerant JSON parsing
> - FastAPI async REST API with file validation, UUID-based storage, and auto-cleanup
> - Streamlit dashboard with interactive risk visualization and downloadable reports
>
> 🔗 GitHub: [your-github-link] | 🚀 Live Demo: [your-demo-link]

---

## 💬 30 Technical Interview Questions & Answers

---

### SECTION 1: Software Engineering & Architecture (Q1–Q10)

---

**Q1. Walk me through the architecture of your AI Contract Risk Analyzer.**

**A:** The system has three layers:
1. **Streamlit Frontend** — handles file upload and result display
2. **FastAPI Backend** — REST API with two routers: upload and analysis
3. **Service Layer** — five specialized services forming a pipeline

The analysis pipeline is: PDF → `PDFExtractor` → `TextCleaner` → `ClauseExtractor` → `RiskAnalyzer` + `SummaryGenerator` → structured JSON response. All external AI calls are abstracted behind a `GeminiService` adapter, so if I switch from Gemini to GPT-4, only one file changes.

---

**Q2. Why did you choose FastAPI over Flask or Django?**

**A:** Three main reasons:
- **Async support**: AI API calls are I/O-bound; FastAPI's `async/await` lets the server handle other requests while waiting for Gemini to respond, unlike Flask's synchronous model
- **Auto-generated docs**: Swagger UI at `/docs` and ReDoc at `/redoc` are generated from Pydantic models — zero extra work
- **Pydantic integration**: Request/response validation is automatic; if the client sends wrong data types, FastAPI returns a 422 with a clear error before hitting business logic

---

**Q3. Explain the Pipeline Pattern you used and why.**

**A:** The Pipeline Pattern chains transformations where each step's output is the next step's input. In my project:
```
PDF bytes → raw text → clean text → clauses → risk analysis → summary → ContractAnalysisResult
```
**Benefits:**
- Each stage is independently testable (I can unit test the text cleaner without touching Gemini)
- Easy to add/remove stages (e.g., add a translation stage between clean and extract)
- Clear single responsibility per service
- Failures are isolated — if risk analysis fails, I can return partial results

---

**Q4. What is the Adapter Pattern and where did you apply it?**

**A:** The Adapter Pattern wraps a third-party interface behind your own interface. I applied it in `GeminiService` — instead of calling `google.generativeai` directly throughout the codebase, all 4 services call `gemini_service.generate_structured_output()`.

**Benefits:**
- Switching from Gemini to OpenAI means changing only `GeminiService` — zero changes to business logic
- Easy to mock in tests (`mock.patch('services.gemini_service.GeminiService')`)
- Centralized retry logic, rate limiting, and error handling

---

**Q5. How does your Settings/Configuration pattern work?**

**A:** I use Pydantic `BaseSettings` in `app/config.py`. It reads from environment variables and validates types at startup. Key design decisions:
- `@lru_cache()` on `get_settings()` — creates one instance, reused across all requests (singleton behavior without a class singleton)
- Fail-fast: if `GEMINI_API_KEY` is empty, the validator catches it immediately at server start, not mid-request
- `.env.example` committed to git; `.env` is gitignored — never expose secrets

---

**Q6. How do you handle file security in the upload endpoint?**

**A:** Four layers of defense:
1. **Extension check**: Only `.pdf` allowed
2. **MIME type validation**: Read first 1024 bytes and check magic bytes (not just extension — attackers can rename `.exe` to `.pdf`)
3. **Size limit**: Configurable via `MAX_FILE_SIZE_MB` (default 10MB) — prevents denial-of-service via huge uploads
4. **UUID filename**: Generated server-side, never using client-provided names — prevents path traversal attacks like `../../etc/passwd`
5. **Auto-deletion**: File deleted after analysis completes (GDPR-compliant, minimizes storage exposure)

---

**Q7. Why do you use async/await throughout the services?**

**A:** The bottleneck in this application is network I/O — waiting for Gemini API responses (typically 5–15 seconds per call). With `async/await`:
- While waiting for Gemini, the FastAPI event loop can process other incoming requests
- For a single contract, I make 3–7 Gemini calls; async prevents thread blocking
- If I later add concurrent clause processing (`asyncio.gather`), the foundation is already async

---

**Q8. How do you handle errors when Gemini returns malformed JSON?**

**A:** The `GeminiService` has a multi-layer fallback:
1. First tries `json.loads()` directly on the response
2. If that fails, uses regex to extract the first `{...}` or `[...]` block from the text (Gemini sometimes wraps JSON in markdown code fences)
3. Cleans common issues: trailing commas, Python-style booleans (`True`/`False` → `true`/`false`)
4. If all parsing fails, logs the raw response and raises a `ValueError` with context
5. The calling service catches this and returns a graceful partial result rather than a 500 error

---

**Q9. Explain your logging strategy.**

**A:** I use Loguru instead of Python's standard `logging` module because:
- Cleaner API — `from utils.logger import logger; logger.info("message")` vs. getting named logger instances
- Automatic formatting with colors, timestamps, and file/line info in terminal
- Built-in rotating file handler (logs rotate at 10MB, keep 30 days)
- Structured logging: `logger.bind(file_id=file_id).info("Processing started")` adds context to every log line

---

**Q10. How would you scale this application to handle 1000 concurrent users?**

**A:** Several strategies:
1. **Horizontal scaling**: Run multiple FastAPI instances behind a load balancer (Nginx/AWS ALB)
2. **Message queue**: Move analysis to background jobs with Celery + Redis — upload returns immediately, client polls for results
3. **Gemini rate limits**: Implement token bucket rate limiting per user; cache results for identical documents (hash-based)
4. **File storage**: Replace local `uploads/` with S3/GCS — shared across all instances
5. **Database**: Add PostgreSQL to persist analysis results — no reprocessing same contract twice
6. **CDN**: Serve Streamlit as a Next.js app behind CloudFront for global distribution

---

### SECTION 2: GenAI & LLM Questions (Q11–Q20)

---

**Q11. What is prompt engineering and how did you apply it in this project?**

**A:** Prompt engineering is the practice of crafting inputs to LLMs to get reliable, structured, and accurate outputs. Techniques I used:

| Technique | Where Used | Why |
|-----------|-----------|-----|
| Role prompting | All prompts | "You are a senior legal analyst" — sets expertise context |
| Structured output | Clause extraction | JSON schema in prompt enforces consistent response format |
| Few-shot examples | Clause prompts | 1 example input/output shows Gemini exactly what to return |
| Scoring rubric | Risk analysis | Explicit 0-100 scale definition prevents score drift |
| Chain-of-thought | Risk prompts | "Think step by step" improves reasoning quality |
| Constraint injection | All prompts | "Return ONLY valid JSON, no markdown" prevents parsing failures |

---

**Q12. What is the difference between zero-shot, one-shot, and few-shot prompting?**

**A:**
- **Zero-shot**: Ask the model directly with no examples. Best for simple, well-understood tasks. `"Classify this text as positive or negative."`
- **One-shot**: Provide one example of input/output before the actual query. Reduces ambiguity.
- **Few-shot**: Provide 2–5 examples. Most reliable for complex structured outputs like JSON extraction. I used one-shot in clause extraction — one example contract snippet with expected clause output — which significantly improved consistency.

---

**Q13. How do you prevent Gemini from hallucinating clause content?**

**A:** Three strategies:
1. **Grounding**: The prompt explicitly says "Extract ONLY clauses that appear verbatim in the contract text. Do NOT invent or infer clauses." This anchors the model to the source document.
2. **Confidence scoring**: I ask Gemini to include a `confidence` field (0.0–1.0). In post-processing, I filter out clauses with confidence < 0.6.
3. **Verbatim extraction**: Ask for `original_text` from the contract alongside the extracted clause. If it doesn't match what's in the document, it's a hallucination indicator.

---

**Q14. Explain the concept of context window and how it affects your application.**

**A:** The context window is the maximum number of tokens (roughly words) an LLM can process in a single call. Gemini 1.5 Flash has a 1M token context window.

**Impact on my project:**
- Short contracts (<10 pages): Sent in a single API call — simple and fast
- Long contracts (>50 pages): I implemented a chunking strategy — split into 4000-token chunks with 200-token overlap (to not lose context at boundaries), extract clauses from each chunk, then deduplicate by clause type
- Trade-off: Chunking increases API calls and cost but handles arbitrarily large documents

---

**Q15. What is temperature in LLM APIs and what value did you use?**

**A:** Temperature controls randomness in token selection:
- `0.0` = deterministic, always picks highest-probability token (best for structured/factual tasks)
- `1.0` = creative, more diverse outputs
- `2.0` = very random/creative

**My choice**: `temperature=0.1` for all prompts. Legal analysis needs consistency — running the same contract twice should give identical clause classifications and similar risk scores. Low temperature achieves this while allowing slight variation for natural language explanations.

---

**Q16. How does your risk scoring algorithm work? Is it purely AI or hybrid?**

**A:** It's **hybrid** — AI + algorithmic post-processing:
1. **Gemini assigns**: raw risk level (Low/Medium/High) and a raw score (0–100) for each clause
2. **Algorithmic calibration**: I apply clause-type weights. A termination clause without notice period gets multiplied by 1.3x; a missing liability cap gets 1.5x
3. **Overall score**: Weighted average across all clause scores, with high-risk clauses weighted 3x more than low-risk ones
4. **Normalization**: Final score clamped to 0–100

**Why hybrid?** Pure AI scores are inconsistent across calls. The algorithmic layer provides stability and makes the scoring defensible — I can explain exactly why a score is 75 vs 70.

---

**Q17. What is RAG and how would you add it to this project?**

**A:** RAG = Retrieval-Augmented Generation. Instead of relying solely on the LLM's training data, you retrieve relevant documents from a knowledge base and include them in the prompt context.

**How I'd add it:**
1. Build a vector database (Pinecone/ChromaDB) of known risky contract clauses from case law and contracts
2. When analyzing a new clause, embed it → retrieve the top-3 most similar risky clauses from history
3. Inject those examples into the risk analysis prompt: "Here are 3 similar clauses that were flagged as high risk in past contracts: [examples]. Analyze this clause accordingly."

**Benefit**: Model makes decisions informed by real precedent, not just training data. Reduces hallucination. Makes risk analysis explainable.

---

**Q18. What are Gemini's safety settings and how did you configure them?**

**A:** Gemini has four harm categories with configurable thresholds: `HARASSMENT`, `HATE_SPEECH`, `SEXUALLY_EXPLICIT`, `DANGEROUS_CONTENT`. Each can be set to `BLOCK_NONE`, `BLOCK_LOW_AND_ABOVE`, `BLOCK_MEDIUM_AND_ABOVE`, or `BLOCK_ONLY_HIGH`.

**My configuration**: Set all to `BLOCK_MEDIUM_AND_ABOVE` (default). For legal contract analysis, this is appropriate — contracts may reference violence/crime in indemnification clauses without being harmful content. If I were processing criminal law contracts, I'd set more permissive thresholds to avoid blocking legitimate legal language.

---

**Q19. How do you handle Gemini API rate limits?**

**A:** Three-layer approach:
1. **Retry with exponential backoff**: `GeminiService` retries up to 3 times with `2^attempt` second delays (2s, 4s, 8s) on `429 Too Many Requests`
2. **Graceful degradation**: If all retries fail, the service returns a partial result rather than crashing the entire analysis
3. **Future**: Implement a token bucket rate limiter in Redis to track requests per minute per user before they hit Gemini — proactive rather than reactive

---

**Q20. What's the difference between Gemini 1.5 Flash and Gemini 1.5 Pro? Why did you choose Flash?**

**A:**
| Aspect | Flash | Pro |
|--------|-------|-----|
| Speed | ~2x faster | Slower |
| Cost | ~10x cheaper | More expensive |
| Accuracy | Good for structured tasks | Better for complex reasoning |
| Context | 1M tokens | 1M tokens |

**I chose Flash** because:
- Contract clause extraction is a structured extraction task, not complex reasoning — Flash handles it well
- Speed matters for user experience (30s vs 60s analysis time)
- Cost matters for a portfolio project with a free API tier
- I can always upgrade to Pro for specific steps (like executive summary) if quality is insufficient

---

### SECTION 3: System Design Questions (Q21–Q25)

---

**Q21. Design the database schema if you were to add PostgreSQL.**

**A:** See the Database Schema section below in this document.

---

**Q22. How would you add user authentication to this system?**

**A:**
1. **Auth service**: Use `python-jose` for JWT tokens, `passlib` for bcrypt password hashing
2. **New endpoints**: `POST /auth/register`, `POST /auth/login` → returns `access_token`
3. **Dependency injection**: FastAPI `Depends(get_current_user)` on all protected routes
4. **Database**: `users` table with `id`, `email`, `hashed_password`, `created_at`
5. **Analysis history**: Link `ContractAnalysis` records to `user_id` — users see only their own analyses
6. **Rate limiting**: Per-user API call limits to prevent abuse

---

**Q23. How would you implement async background processing?**

**A:** Replace synchronous analysis with Celery + Redis:
1. `POST /analyze/{file_id}` → creates a Celery task, returns `task_id` immediately (202 Accepted)
2. Celery worker runs analysis in background
3. `GET /analyze/status/{task_id}` → client polls for status (`pending`/`processing`/`complete`/`failed`)
4. Results stored in Redis (short-term) and PostgreSQL (long-term)
5. Optional: WebSocket endpoint for real-time progress updates

**Why?** Current sync approach blocks the server for 30s per request. With Celery, the API can accept thousands of requests instantly.

---

**Q24. How would you implement multi-document comparison?**

**A:**
1. User uploads 2+ contracts → both get file_ids
2. New endpoint: `POST /compare` with body `{file_ids: ["id1", "id2"]}`
3. Pipeline runs analysis on both documents
4. New `ComparisonService`: diffs clause-by-clause using embeddings (cosine similarity) to match equivalent clauses across documents
5. Returns a `ContractComparison` model with: matched clauses, risk score deltas, clauses present in one but not the other
6. Frontend shows side-by-side view with color-coded differences

---

**Q25. How would you add contract version comparison (redlining)?**

**A:**
1. Store contracts with a `version` field per `contract_group`
2. Use difflib (Python built-in) for text-level diff between versions
3. For clause-level diff: compare extracted clauses using sentence embeddings (sentence-transformers)
4. Gemini prompt: "Given these two versions of a termination clause, identify what changed and whether the new version is more or less favorable to the client"
5. Return a `RedlineReport` with: changed clauses, risk score changes, AI explanation of each change's legal implication

---

### SECTION 4: Prompt Engineering Deep Dive (Q26–Q30)

---

**Q26. Show an example of a well-engineered prompt vs a bad prompt.**

**A:**

**❌ Bad Prompt:**
```
Extract clauses from this contract: {contract_text}
```
Problems: No role, no format, no constraints — output is unpredictable.

**✅ Good Prompt (mine):**
```
You are a senior legal analyst with 20 years of experience reviewing commercial contracts.

TASK: Extract and classify all legal clauses from the contract text below.

RULES:
1. Extract ONLY clauses that appear in the contract text — do not invent clauses
2. Classify each clause into exactly one of these types: [Payment Terms, Termination, ...]
3. Return ONLY valid JSON matching this schema exactly — no markdown, no explanation

OUTPUT FORMAT:
{"clauses": [{"clause_type": "...", "original_text": "...", "summary": "...", "confidence": 0.95}]}

EXAMPLE INPUT: "Payment shall be due within 30 days of invoice."
EXAMPLE OUTPUT: {"clauses": [{"clause_type": "Payment Terms", "original_text": "Payment shall be due within 30 days of invoice.", "summary": "30-day payment terms", "confidence": 0.98}]}

CONTRACT TEXT:
{contract_text}
```

---

**Q27. What is chain-of-thought prompting and why does it help with risk analysis?**

**A:** Chain-of-thought (CoT) prompting asks the model to reason step-by-step before giving an answer, rather than jumping directly to a conclusion.

**Example in my risk analysis prompt:**
```
Analyze this clause for risk. Think through this systematically:
1. What does this clause allow/require each party to do?
2. What is the worst-case scenario if this clause is exercised?
3. Is there a notice period, limitation, or cap that protects the client?
4. Based on this reasoning, assign a risk score 0-100.
```

**Why it helps**: Without CoT, Gemini might assign a risk score based on surface-level pattern matching. With CoT, it actually reasons through the legal implications, producing more accurate and explainable scores.

---

**Q28. How do you ensure consistent JSON output from Gemini?**

**A:** Five techniques:
1. **Explicit schema**: Provide the exact JSON structure in the prompt
2. **Negative constraint**: "Return ONLY valid JSON. Do NOT include markdown code fences, explanations, or any text before/after the JSON"
3. **One-shot example**: Show exactly one input/output pair so the format is demonstrated, not just described
4. **Response MIME type**: Set `response_mime_type="application/json"` in the Gemini API call — newer versions support this natively
5. **Fallback parser**: Regex extraction of `{...}` blocks as a safety net for when the model still adds surrounding text

---

**Q29. How would you evaluate prompt quality objectively?**

**A:**
1. **Accuracy**: Run 20 known contracts with manually labeled clauses → measure F1 score (precision + recall of clause extraction)
2. **Consistency**: Run the same contract 10 times → measure variance in risk scores (should be < ±5 points)
3. **Format compliance**: Measure JSON parse success rate — target >99%
4. **Hallucination rate**: Sample extracted clauses → manually verify they appear verbatim in source document
5. **A/B testing**: Two prompt variants on the same test set → compare metrics

This is called **prompt evaluation** or **LLM evals** — a critical skill in production GenAI systems.

---

**Q30. What would you do differently if you had to rebuild this project for production at scale?**

**A:**
1. **Async everything**: Move to Celery/Redis for background processing
2. **Vector DB**: Add embeddings for clause similarity search (RAG)
3. **Prompt versioning**: Store prompts in a database with version IDs — A/B test prompt changes like code changes
4. **Observability**: Add LLM-specific tracing (LangSmith/Langfuse) to track token usage, latency, and accuracy per prompt
5. **Cost optimization**: Cache Gemini responses by document hash — same contract = no API call
6. **Multi-model**: Route simple tasks to Flash, complex reasoning to Pro — cost vs. quality tradeoff per step
7. **Human-in-the-loop**: For risk score > 80, flag for human legal review before showing to client
8. **CI/CD**: GitHub Actions pipeline running prompt evals on every PR that touches prompt files

---

## 🗄️ Database Schema (PostgreSQL — Future Enhancement)

```sql
-- Users table (for authentication)
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name   VARCHAR(255),
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active   BOOLEAN DEFAULT TRUE
);

-- Contract uploads table
CREATE TABLE contracts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    filename        VARCHAR(500) NOT NULL,
    file_size_bytes INTEGER,
    total_pages     INTEGER,
    upload_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Store hash for deduplication / caching
    content_hash    VARCHAR(64),
    UNIQUE(user_id, content_hash)
);

-- Analysis results table
CREATE TABLE analyses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id         UUID REFERENCES contracts(id) ON DELETE CASCADE,
    overall_risk_score  INTEGER CHECK (overall_risk_score BETWEEN 0 AND 100),
    overall_risk_level  VARCHAR(10) CHECK (overall_risk_level IN ('Low', 'Medium', 'High')),
    processing_time_sec DECIMAL(6,2),
    gemini_model        VARCHAR(100),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Full result JSON (denormalized for fast retrieval)
    result_json         JSONB
);

-- Extracted clauses table
CREATE TABLE clauses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id     UUID REFERENCES analyses(id) ON DELETE CASCADE,
    clause_type     VARCHAR(100) NOT NULL,
    original_text   TEXT NOT NULL,
    summary         TEXT,
    confidence      DECIMAL(3,2) CHECK (confidence BETWEEN 0 AND 1),
    risk_level      VARCHAR(10) CHECK (risk_level IN ('Low', 'Medium', 'High')),
    risk_score      INTEGER CHECK (risk_score BETWEEN 0 AND 100),
    explanation     TEXT,
    recommendation  TEXT
);

-- Missing clauses table
CREATE TABLE missing_clauses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id     UUID REFERENCES analyses(id) ON DELETE CASCADE,
    clause_type     VARCHAR(100) NOT NULL,
    severity        VARCHAR(10) CHECK (severity IN ('Low', 'Medium', 'High', 'Critical')),
    description     TEXT,
    recommendation  TEXT
);

-- Executive summaries table
CREATE TABLE executive_summaries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id         UUID REFERENCES analyses(id) ON DELETE CASCADE UNIQUE,
    summary_text        TEXT NOT NULL,
    key_obligations     TEXT[],
    key_risks           TEXT[],
    recommended_actions TEXT[]
);

-- Indexes for common queries
CREATE INDEX idx_contracts_user_id ON contracts(user_id);
CREATE INDEX idx_analyses_contract_id ON analyses(contract_id);
CREATE INDEX idx_clauses_analysis_id ON clauses(analysis_id);
CREATE INDEX idx_clauses_risk_level ON clauses(risk_level);
CREATE INDEX idx_contracts_hash ON contracts(content_hash);
```

**Design Notes (explain in interviews):**
- `content_hash` on contracts enables caching — same document uploaded twice by same user reuses analysis
- `result_json JSONB` on analyses allows fast full-result retrieval without joining 5 tables for every API response
- `ON DELETE CASCADE` ensures no orphaned records if a contract is deleted (GDPR right-to-erasure)
- Separate `executive_summaries` table (1:1 with analyses) keeps the main table lean

---

## 🚀 Deployment Guide

### Option 1: Streamlit Cloud (Free — Frontend Only)

```bash
# 1. Push project to GitHub

# 2. Go to share.streamlit.io
# 3. Click "New app" → Select repo → Set:
#    Main file path: frontend/streamlit_app.py
#    Python version: 3.11

# 4. Add secrets (Settings → Secrets):
BACKEND_URL = "https://your-render-backend.onrender.com"
# (No Gemini key here — it lives on the backend)
```

### Option 2: Render (Free tier — Backend)

```bash
# render.yaml (place in project root)
services:
  - type: web
    name: contract-risk-analyzer-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: GEMINI_API_KEY
        sync: false   # Set manually in Render dashboard
      - key: DEBUG
        value: "False"
      - key: UPLOAD_DIR
        value: "/tmp/uploads"
```

### Option 3: Railway (Full-stack)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up

# Set environment variables
railway variables set GEMINI_API_KEY=your_key_here
railway variables set DEBUG=False

# Get your deployment URL
railway status
```

### Option 4: Docker (Production)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p uploads

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t contract-analyzer .
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key .

# Or with docker-compose
docker-compose up --build
```

---

## 🔮 Future Enhancements (Explain in Interviews)

| Enhancement | Technology | Interview Talking Point |
|-------------|-----------|------------------------|
| **RAG Pipeline** | Pinecone + LangChain | "I'd embed each extracted clause and store in a vector DB. During analysis, retrieve similar risky clauses from history to ground the AI's assessment" |
| **Multi-doc Comparison** | Sentence Transformers | "Embed clauses from both contracts, cosine similarity to match equivalent sections, then diff the matched pairs" |
| **Redline Suggestions** | Gemini + difflib | "Ask Gemini to rewrite high-risk clauses with specific changes, then use difflib to highlight exactly what changed" |
| **Contract Templates** | Vector similarity | "When a missing clause is detected, retrieve the top-3 similar standard clauses from a template library" |
| **PostgreSQL persistence** | SQLAlchemy + Alembic | "Add auth, analysis history, and content-hash caching to avoid reprocessing identical documents" |
| **Batch processing** | Celery + Redis | "Move from sync to async task queue — upload returns task_id, client polls for completion" |
| **LLM Observability** | LangSmith/Langfuse | "Track every Gemini call: tokens used, latency, prompt version — essential for cost management in production" |
| **Contract Classification** | Fine-tuned classifier | "Before clause extraction, classify contract type (SaaS/employment/NDA) and use type-specific prompts" |
