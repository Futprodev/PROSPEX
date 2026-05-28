# PROSPEX

AI-powered weekly financial and regulatory briefing platform for Dutch FinTech SMEs. Connects to Xero accounting, monitors EU/NL regulatory sources, and generates plain-language briefings via Groq LLM — no finance jargon, no fluff.

## What it does

Each week, for every connected company:
1. Pulls the latest P&L, balance sheet, and cash position from Xero
2. Scores 5 financial health dimensions (liquidity, profitability, runway, receivables, trend)
3. Retrieves relevant regulatory updates (GDPR, AML, DORA, MiCA, PSD2) via semantic search
4. Generates a plain-language briefing with concrete action items and deadlines
5. Surfaces everything through a clean dashboard with light/dark mode

## Dashboard features

- **Health score card** — current score, week-over-week delta, colour-coded
- **Score trend chart** — line chart of historical health scores
- **Revenue vs expenses chart** — 11-month bar chart pulled from Xero P&L
- **Cash flow forecast** — 12-month linear projection from current cash + burn, flags the month cash runs out
- **Dimension breakdown** — coloured bars for each of the 5 financial dimensions with insight text
- **Industry benchmark card** — side-by-side comparison of gross margin, runway, and DSO vs industry good/average/poor thresholds
- **Ask your data** — chat input that answers free-form questions about the company's snapshot and latest briefing via Groq
- **Weekly briefing** — three sections (Financial Alerts, Regulatory Updates, This Week's Actions) with accented borders per section
- **Briefing history** — past briefings in the sidebar plus a full History page
- **PDF export** — print-friendly view of any briefing for sharing or filing
- **Company menu** — single dropdown in the header showing the connected company name; contains Sync Xero, Generate Briefing, Reconnect Xero, Delete company, and the next-auto-run timestamp
- **First-connect flow** — fresh installs land on a "Connect your Xero" screen; clicking through OAuth automatically creates the company row (name pulled from Xero), sets it as active via cookie, and lands the user on the dashboard with zero config
- **Strict delete** — deleting a company requires typing its exact name. Cascading FKs wipe all briefings and snapshots in one step. After delete, the dashboard returns to the connect screen
- **Dark / light mode** — toggle in the header, respects system preference, persists across sessions

## Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, APScheduler |
| Database | Supabase (PostgreSQL + pgvector) |
| Embeddings | BGE-base-en-v1.5 (sentence-transformers, CPU) |
| LLM | Groq API (llama-3.3-70b-versatile) |
| Accounting | Xero API (OAuth2 PKCE) |
| Frontend | Next.js 14, Tailwind CSS, shadcn/ui, Recharts, next-themes |

## Project structure

```
prospex/
├── backend/
│   ├── agent/          # LLM provider, prompts, briefing pipeline
│   ├── api/            # FastAPI route definitions
│   ├── db/             # Supabase client, schema SQL
│   ├── rag/            # Regulation retriever (pgvector cosine search)
│   ├── regulations/    # Scraper (AFM, EBA, EUR-Lex), filter, embedder
│   ├── scheduler/      # Weekly APScheduler job
│   ├── scoring/        # Financial scoring engine + benchmarks
│   ├── xero/           # OAuth2 auth, data pull, parser
│   ├── tests/          # Per-module verification scripts
│   ├── main.py         # FastAPI app entry point
│   ├── requirements.txt
│   └── config.py
└── frontend/
    ├── app/            # Next.js App Router pages
    ├── components/     # UI components (shadcn/ui + custom)
    └── lib/            # Typed API client, helpers
```

## Backend setup

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
SUPABASE_ANON_KEY=your-anon-key
XERO_CLIENT_ID=your-xero-client-id
XERO_CLIENT_SECRET=your-xero-client-secret
XERO_REDIRECT_URI=https://your-ngrok-url/callback
GROQ_API_KEY=your-groq-api-key
```

### 3. Set up the database
Run these in the Supabase SQL Editor in order:
- `backend/db/schema.sql` — creates the 4 core tables
- `backend/db/schema_rag.sql` — creates the pgvector similarity search function

Disable row-level security on all 4 tables (Supabase dashboard → Table Editor → RLS).

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
python regulations/scraper.py   # fetch from AFM, EBA, EUR-Lex
python regulations/embedder.py  # chunk + embed (downloads ~440 MB model on first run)
```

### 6. Start the backend
```bash
uvicorn main:app --reload --port 8000
```

The scheduler runs automatically every Monday at 07:00 Amsterdam time. To trigger manually, use the dashboard or call `POST /companies/{id}/briefings/generate`.

## Frontend setup

### Prerequisites
- Node.js 20+

### 1. Install dependencies
```bash
cd frontend
npm install
```

### 2. Configure environment
Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_COMPANY_ID=your-company-uuid
```

### 3. Start the dev server
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Module status

| # | Module | Status |
|---|---|---|
| 1 | Database + config | Done |
| 2 | Xero OAuth2 + data pull | Done |
| 3 | Financial scoring engine | Done |
| 4 | Regulation scraper + RAG | Done |
| 5 | LLM briefing agent | Done |
| 6 | FastAPI + scheduler | Done |
| 7 | Next.js dashboard | Done |

## Notes

- For the in-app **Connect / Reconnect Xero** buttons to work, set `XERO_REDIRECT_URI=http://localhost:8000/xero/callback` in `backend/.env` and add the same URL to your Xero app's allowed redirect URIs in the Xero developer portal. Optionally set `FRONTEND_URL=http://localhost:3000` (defaults to that already). The CLI `xero/auth_server.py` script still works as a fallback on port 8080.
- After a successful connect, the callback sets a `prospex_company_id` cookie scoped to `localhost`. Both the FastAPI backend (port 8000) and the Next.js frontend (port 3000) see the same cookie because cookies are not port-scoped — so no env editing is needed when swapping companies.
- If your Supabase tables were created before the current `schema.sql` was committed, run this once to add cascading deletes:
  ```sql
  alter table briefings           drop constraint if exists briefings_company_id_fkey;
  alter table briefings           add  constraint briefings_company_id_fkey
       foreign key (company_id) references companies(id) on delete cascade;
  alter table financial_snapshots drop constraint if exists financial_snapshots_company_id_fkey;
  alter table financial_snapshots add  constraint financial_snapshots_company_id_fkey
       foreign key (company_id) references companies(id) on delete cascade;
  ```
- `.env` and `.env.local` are git-ignored — never commit secrets
- Xero Demo Company does not support aged receivables (401) — this is skipped gracefully
- BGE model downloads ~440 MB on first run of `embedder.py`
- Groq falls back through a model list if the primary model is unavailable; if Groq is unreachable entirely, a deterministic template briefing is generated from raw scores so the user is never shown an empty page
- Regulatory filter ignores EBA procedural documents (RTS/ITS/supervisory peer reviews) — only flags GDPR, AML, DORA, MiCA, and PSD2 which are the regulations that actually require SME action
- The revenue/expense chart shows up to 11 months of P&L (Xero's API limit for a single monthly query). For more history, the Xero call would need to be split into multiple sequential pulls — planned as a follow-up feature

## Roadmap

Implemented:
- Score trend chart
- Revenue vs expenses chart
- PDF export of briefings
- Cash flow forecasting (12 months out, linear projection)
- Benchmark comparison vs industry averages
- Xero connect/reconnect through the UI
- "Ask your data" chat input on the dashboard
- Multi-company support with a company switcher
- Sync Xero / Generate Briefing buttons + scheduler "next run" indicator

Planned:
- Multi-year historical P&L (sequential Xero pulls)
- Email delivery of the weekly briefing
- Non-linear cash forecast (seasonality, recurring vs one-off)
- Conversation memory for the "Ask your data" chat
