-- Run this in the Supabase SQL editor (Dashboard → SQL Editor → New Query)
-- Enable pgvector extension first (required for regulation embeddings)
create extension if not exists vector;

-- TABLE 1: companies
-- One row per business that connects their Xero account.
-- Stores OAuth tokens so we can pull data without re-authenticating each time.
create table if not exists companies (
    id                  uuid primary key default gen_random_uuid(),
    name                text not null,
    country             text not null default 'NL',
    industry            text not null default 'fintech',
    xero_tenant_id      text,
    xero_access_token   text,
    xero_refresh_token  text,
    token_expires_at    timestamptz,
    created_at          timestamptz not null default now()
);

-- TABLE 2: financial_snapshots
-- One row per weekly Xero data pull.
-- Stores both the raw Xero JSON (for re-parsing) and the computed scores.
create table if not exists financial_snapshots (
    id                  uuid primary key default gen_random_uuid(),
    company_id          uuid not null references companies(id) on delete cascade,
    pulled_at           timestamptz not null default now(),
    annual_revenue      numeric,
    gross_margin_pct    numeric,
    monthly_burn        numeric,
    cash                numeric,
    runway_months       numeric,
    dso_days            numeric,
    health_score        numeric,
    data_quality_score  numeric,
    top_risks           jsonb,
    raw_xero_data       jsonb
);

-- TABLE 3: regulation_updates
-- One row per regulation or update fetched from EBA / EUR-Lex.
-- The embedding column stores the BGE vector for semantic search via pgvector.
create table if not exists regulation_updates (
    id          uuid primary key default gen_random_uuid(),
    fetched_at  timestamptz not null default now(),
    source      text,
    title       text,
    url         text unique,
    date        text,
    summary     text,
    full_text   text,
    embedding   vector(768),
    is_relevant boolean
);

-- TABLE 4: briefings
-- One row per generated briefing.
-- Stores both structured fields and the full plain-text briefing shown to the user.
create table if not exists briefings (
    id                  uuid primary key default gen_random_uuid(),
    company_id          uuid not null references companies(id) on delete cascade,
    generated_at        timestamptz not null default now(),
    week_of             date,
    financial_summary   text,
    regulatory_summary  text,
    action_items        jsonb,
    full_briefing       text,
    health_score        numeric
);

-- Index for fast retrieval of latest snapshot per company
create index if not exists idx_snapshots_company_pulled
    on financial_snapshots(company_id, pulled_at desc);

-- Index for fast retrieval of latest briefing per company
create index if not exists idx_briefings_company_generated
    on briefings(company_id, generated_at desc);

-- Index for vector similarity search on regulations
create index if not exists idx_regulations_embedding
    on regulation_updates using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);
