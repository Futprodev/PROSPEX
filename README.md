# PROSPEX

AI-powered weekly financial and regulatory briefing platform for Dutch FinTech SMEs. Connects to Xero accounting, monitors EU/NL regulatory sources, and generates plain-language briefings via Groq LLM — no finance jargon, no fluff.

## What it does

Each week, for every connected company:
1. Pulls the latest P&L, balance sheet, and cash position from Xero
2. Scores 5 financial health dimensions (liquidity, profitability, runway, receivables, trend)
3. Retrieves relevant regulatory updates (GDPR, AML, DORA, MiCA, PSD2) via semantic search
4. Generates a plain-language briefing with concrete action items and deadlines
5. Surfaces everything through a clean dashboard with light/dark mode

## Page structure

PROSPEX is one company per install, organised into three primary pages plus a history view. Each page has a deliberate "reading altitude" so the founder knows what to look at when.

- **Dashboard (`/`)** — the 30-second landing.
  - **Hero metrics strip**: Cash · Runway · Monthly burn · Income this month · Net profit, each with delta arrows
  - **Weekly briefing** (2/3 width) + **Health score** and **Dimension breakdown** (1/3 sidebar)
  - That's it. No charts, no debtors, no benchmarks. Just "should I worry?"
- **Briefing (`/briefing`)** — the advisory deep dive.
  - Full weekly briefing
  - Health score + score trend chart + dimension breakdown + industry benchmarks
  - Past briefings list (also linked from `/briefings`)
- **Financials (`/financials`)** — the financial deep dive. Pure description, no AI advisory.
  - Hero metrics strip
  - "What changed" card (week-over-week deltas: cash, DSO, burn, health)
  - Revenue vs expenses chart + 12-month cash forecast (50:50)
  - Where your money goes (expense categories) + Who owes you (debtors) (50:50)
- **History (`/briefings`)** — flat list of every briefing generated, newest first. Each row links to `/briefings/[id]`.

A **floating "Ask your data" agent pill** lives bottom-right on every page. Click to chat with the LLM about your numbers and the latest briefing.

## Features by area

### Headline metrics
- **Hero strip** on Dashboard and Financials — Cash, Runway, Monthly burn (with % change), Income this month (vs last month), Net profit this month (vs last month). Colour-coded thresholds for runway (red <3mo, amber <6mo, green ≥6mo) and net profit (red if negative).
- **What changed card** — Cash · DSO · Burn · Health score deltas with up/down arrows tinted by whether the change is good or bad (e.g. lower DSO is good and shows green).

### Charts
- **Score trend chart** — line chart of historical health scores
- **Revenue vs expenses chart** — bar chart pulled from Xero P&L, oldest → newest, empty months filtered out
- **Cash flow forecast** — 12-month linear projection from current cash + burn, flags the month cash runs out, red zero-line

### Operational breakdowns
- **Where your money goes** — top expense categories ranked by total spend, with a stacked-bar overview and per-category percentage
- **Who owes you** — top 5 debtors with current vs 60+ day overdue split, colour-coded when overdue percentage is high

### AI advisory
- **Weekly briefing** — three accented sections (Financial Alerts, Regulatory Updates, This Week's Actions). Markdown stripping built into the parser so stray `##` headers never reach the UI.
- **Dimension breakdown** — five coloured bars for liquidity, profitability, runway, receivables, cash flow trend with plain-language insight per dimension
- **Industry benchmark card** — your gross margin, runway, and DSO plotted against good/average/poor industry thresholds
- **Briefing history** + **PDF export** — print-friendly briefing page, no chrome or buttons in the printout

### Background pipeline
- **Sync Xero** — pull-only; re-parses and saves a new `financial_snapshots` row
- **Generate Briefing** — full pipeline: pull + score + RAG + LLM + save
- **Progress banner** — sticky banner under the header shows live status for either job, polling every 3s, with a 2-minute stall detector. Survives page reloads via localStorage.
- **Scheduler** — APScheduler runs the full pipeline every Monday 07:00 Amsterdam time. Next-run timestamp visible in the company menu.

### Company management (single-company per install)
- **First-connect screen** — fresh installs land on "Connect your Xero". One click → OAuth → company row created (name pulled from Xero) → cookie set → dashboard renders. Zero env editing.
- **Company menu in the header** — Sync, Generate, Reconnect, Delete, plus "Next auto-run".
- **Strict delete** — must type the exact company name. Cascading FKs wipe all briefings + snapshots. Returns to the connect screen.
- **Dark / light mode** — header toggle, respects system preference, persists across sessions.

### Ask your data (agent chat)
- Floating pill bottom-right on every page; click to open a 420px chat panel
- **Conversation memory** — the last 12 messages are sent with every new question, so follow-ups ("tell me more", "the second one") work
- **Per-company localStorage** — refresh the page and your conversation is still there. Clear button (🗑) explicitly wipes it.
- Suggestion chips on first open so the user knows what to ask

## LLM agent — what it knows and where it stops

The chat agent (and the weekly briefing generator that shares its provider) runs on Groq's free tier (`llama-3.3-70b-versatile` with fallbacks to other Llama variants and Mixtral). Every question is answered against a freshly-assembled context that includes:

- Company profile (name, industry, country)
- Latest snapshot — cash, annual revenue, monthly burn, runway, DSO, gross margin
- **Top expense categories** with total spend, current-month value, and per-month average
- **Top debtors** with current vs 60+ day overdue split
- All **5 financial dimension scores** (score, label, insight) parsed from the latest briefing
- **Full text of the latest briefing** (up to 4,000 characters)
- **Last 12 messages** of the current conversation, for follow-ups

That's enough for the agent to answer concrete questions like:
- *"What's my third-biggest expense?"* → reads the ranked list
- *"Why is my runway score so low?"* → references the dimension's insight text
- *"Who's the worst late payer?"* → reads the debtor list
- *"Tell me more about that"* → uses conversation history to resolve "that"

### Limitations — what it can't do (yet)

| Limitation | Why | Workaround |
|---|---|---|
| **No live calculations** — can't run "what if my burn dropped 20%?" | The LLM only sees stored numbers, not a calculator | Add a forecast scenario UI, or wire the chat to a calculator tool |
| **No fresh data on demand** — can't say "what's my Xero balance right now?" | The agent reads the most recent saved snapshot, not Xero live | Click Sync Xero first, then ask |
| **No multi-week comparison** — can't say "compare this week vs four weeks ago" cleanly | Only the latest snapshot is in context | Pass a history array — planned |
| **No on-demand regulation lookup** — can answer about regs only as far as the briefing summarises them | RAG retrieval runs during briefing generation, not at chat time | Wire pgvector search into the chat path — planned |
| **No memory across `Clear` or different companies** | Conversation history is scoped to `prospex_chat_${company_id}` in browser localStorage | This is the intended trade-off — clear is a hard reset |
| **Briefing text capped at 4,000 chars in chat context** | Keeps prompt size predictable on Groq free tier | Raise if you upgrade to a larger plan |
| **No tool use / function calling** — the agent can only respond with text | We use the Groq chat API in plain-completion mode, no tools registered | Add tools when there's a clear use case (e.g. "compute runway under X scenario") |
| **No conversation memory across devices** | localStorage is per-browser | Move conversation persistence to Supabase — planned |
| **Token-limited follow-ups** — after ~6 Q&A pairs the oldest gets dropped | We trim history to last 12 messages | Increase the cap, or summarise old turns |
| **Demo Company can't populate debtors** | Xero gates Aged Receivables by Contact on Demo tenants (401) — see Notes | Use a real Xero connection or a free-trial tenant |
| **No personally identifiable info filtering** | The briefing text and debtor names are sent verbatim to Groq | Acceptable for now; add a PII redaction step before a real product launch |

### Briefing-specific limits
- The weekly briefing pipeline reads up to 11 months of P&L (Xero API limit per call). Older history would require multiple sequential pulls — on the roadmap.
- The LLM is instructed to use **only** plain text (no markdown). A second-line defence in the frontend strips stray `##` and `**bold**` in case the model ignores the rule.
- If Groq is unreachable, a deterministic **TemplateFallback** assembles a briefing from raw scores. The narrative is simpler but the figures are always accurate.
- Regulatory context is filtered to GDPR, AML, DORA, MiCA, and PSD2 only — EBA procedural documents (RTS/ITS/peer reviews) are excluded because they target supervisors, not SMEs.

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
# Optional — bootstrap default if you already have a company in the DB.
# Leave unset for fresh installs; the OAuth callback sets the active-company
# cookie automatically on first connect.
# NEXT_PUBLIC_COMPANY_ID=
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

### Setup gotchas
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
- `.env` and `.env.local` are git-ignored — never commit secrets.
- BGE model downloads ~440 MB on first run of `embedder.py`.

### Xero quirks
- **Xero Demo Company returns 401 for Aged Receivables by Contact.** OAuth scope is granted, but Xero gates this specific report at the tenant level for Demo organisations. P&L, Balance Sheet, and Bank Transactions work fine; only the per-debtor AR report fails. Real customer tenants and 30-day-trial Xero accounts don't have this restriction. The pipeline skips gracefully — the Who Owes You card just shows an empty-state message.
- **Xero returns monthly P&L columns newest-first.** The parser reverses each trend array (revenue, expenses, net profit) so all downstream code can assume oldest → newest. Without this fix, `monthly_burn` averaged the oldest 3 months instead of the newest 3 and the chart rendered backwards.
- **Single-process, single-company prototype.** The active company id lives in a cookie scoped to `localhost`. The first OAuth callback creates it; the Delete action removes it. There's no multi-tenant isolation — adding a real customer would need Supabase RLS + per-user auth.

### Briefing pipeline behaviour
- The revenue/expense chart shows up to 11 months of P&L (Xero's API limit for a single monthly query). For more history, the Xero call would need to be split into multiple sequential pulls — on the roadmap.
- Groq falls back through a model list if the primary model is unavailable; if Groq is unreachable entirely, the **TemplateFallback** generates a deterministic briefing from raw scores so the user is never shown an empty page.
- The system prompt forbids markdown. As a second-line defence, `parseBriefingText()` strips stray `##`, `###`, `**bold**`, and runs of blank lines before rendering.
- Regulatory filter ignores EBA procedural documents (RTS/ITS/supervisory peer reviews) — only flags GDPR, AML, DORA, MiCA, and PSD2 which are the regulations that actually require SME action.

### Print / PDF export
- `@media print` styles preserve background colours and SVG gradient fills (`print-color-adjust: exact`) so the cash forecast and bar chart appear in the PDF. Recharts' `ResponsiveContainer` is forced to a fixed 240px height during print because its `ResizeObserver` doesn't fire during rasterisation.
- Header, nav, buttons, the progress banner, and the chat pill are all hidden in print via `.no-print` / element selectors.

## Roadmap

Implemented:
- Hero metrics strip (cash, runway, burn, income, net profit) with MoM deltas
- "What changed" week-over-week deltas card
- Top debtors card (Aged Receivables by Contact)
- Expense category breakdown with stacked-bar summary
- Score trend chart · revenue vs expenses chart · 12-month cash forecast
- Benchmark comparison vs industry averages
- PDF export of briefings (print-friendly)
- Xero connect / reconnect / delete through the UI
- "Ask your data" agent with enriched context (expenses, debtors, dimensions) and conversation memory
- Sticky progress banner with real polling (no fixed timers)
- Three-page information architecture (Dashboard / Briefing / Financials)

Planned:
- Multi-year historical P&L (sequential Xero pulls beyond the 11-month limit)
- Email delivery of the weekly briefing
- Non-linear cash forecast (seasonality, recurring vs one-off)
- On-demand RAG retrieval inside the chat agent (search regulations when asked)
- Invoices-API fallback for debtors when AR report 401s (e.g. Demo Company)
- Tool use for the agent — calculator, scenario simulation, sync trigger
- Conversation persistence in Supabase instead of localStorage (cross-device)
- PII redaction before sending data to the LLM provider
- Multi-tenant isolation (Supabase RLS + auth) if positioning for paying customers
