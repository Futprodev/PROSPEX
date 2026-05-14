# PROSPEX

AI-powered weekly financial and regulatory briefing platform for Dutch FinTech SMEs. Connects to Xero accounting, monitors EU/NL regulatory sources, and generates plain-language briefings via Groq LLM — no finance jargon.

## What it does

Each week, for every connected company:
1. Pulls the latest P&L, balance sheet, and cash position from Xero
2. Scores 5 financial health dimensions (liquidity, profitability, runway, receivables, trend)
3. Retrieves relevant regulatory updates (GDPR, AML, DORA, MiCA, PSD2) via semantic search
4. Generates a briefing translated into plain language — with concrete action items, no fluff

## Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, APScheduler |
| Database | Supabase (PostgreSQL + pgvector) |
| Embeddings | BGE-base-en-v1.5 (sentence-transformers, CPU) |
| LLM | Groq API (llama-3.3-70b-versatile) |
| Accounting | Xero API (OAuth2 PKCE) |
| Frontend | Next.js (Module 7 — in progress) |

## Project structure

```
prospex/
├── backend/
│   ├── agent/          # LLM provider, prompts, briefing pipeline
│   ├── db/             # Supabase client, schema SQL
│   ├── rag/            # Regulation retriever (pgvector cosine search)
│   ├── regulations/    # Scraper (AFM, EBA, EUR-Lex), filter, embedder
│   ├── scoring/        # Financial scoring engine + benchmarks
│   ├── xero/           # OAuth2 auth, data pull, parser
│   ├── tests/          # Per-module verification scripts
│   ├── requirements.txt
│   └── config.py
└── frontend/           # Next.js app (coming in Module 7)
```

## Setup

### Prerequisites
- Python 3.10+
- Supabase project with pgvector enabled
- Xero developer app (OAuth2, PKCE)
- Groq API key (free tier, ~6k requests/day)

### 1. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment
Create `backend/.env`:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
XERO_CLIENT_ID=your-xero-client-id
XERO_CLIENT_SECRET=your-xero-client-secret
XERO_REDIRECT_URI=https://your-ngrok-url/callback
GROQ_API_KEY=your-groq-api-key
```

### 3. Set up the database
Run these in the Supabase SQL Editor (in order):
- `backend/db/schema.sql` — creates the 4 core tables
- `backend/db/schema_rag.sql` — creates the pgvector similarity search function

### 4. Connect Xero
```bash
cd backend
python xero/auth_server.py
```
Visit the printed URL, authorise with Xero, then run a sync:
```bash
python xero/pull.py
```

### 5. Scrape and embed regulations
```bash
python regulations/scraper.py
python regulations/embedder.py
```

### 6. Generate a briefing
Edit `tests/test_briefing.py` with your company ID, then:
```bash
python tests/test_briefing.py
```

## Module status

| # | Module | Status |
|---|---|---|
| 1 | Database + config | Done |
| 2 | Xero OAuth2 + data pull | Done |
| 3 | Financial scoring engine | Done |
| 4 | Regulation scraper + RAG | Done |
| 5 | LLM briefing agent | Done |
| 6 | FastAPI + scheduler | In progress |
| 7 | Next.js dashboard | Pending |

## Notes

- `.env` is git-ignored — never commit secrets
- The BGE model downloads ~440 MB on first run of `embedder.py`
- Xero Demo Company does not support aged receivables (401) — skipped gracefully
- Groq falls back through a model list if the primary is unavailable; if Groq is unreachable entirely, a template briefing is generated from raw scores
