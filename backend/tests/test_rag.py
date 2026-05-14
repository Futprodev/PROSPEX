"""
Module 4 verification test.

Before running:
1. Open Supabase SQL Editor → run the contents of db/schema_rag.sql once.
   (This creates the match_regulations RPC function used by the retriever.)
2. First run downloads the BGE model (~440 MB) — takes 30s.

Run with:
    cd prospex/backend
    python tests/test_rag.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regulations.scraper   import run_all
from regulations.filter    import filter_all_pending
from regulations.embedder  import embed_all_pending
from rag.retriever         import retrieve_relevant_regulations


def main():
    print("\n" + "═" * 60)
    print("  PROSPEX — Module 4 Regulatory Pipeline + RAG Test")
    print("═" * 60)

    # ── Step 1: Scrape ───────────────────────────────────────────────────
    print("\n[1/4] Scraping regulatory feeds...")
    new_count = run_all(fetch_text=True)

    # ── Step 2: Filter ───────────────────────────────────────────────────
    print("\n[2/4] Filtering for FinTech relevance...")
    relevant, irrelevant = filter_all_pending()

    # ── Step 3: Embed ────────────────────────────────────────────────────
    print("\n[3/4] Embedding relevant regulations...")
    print("      (First run downloads BGE-base — be patient)")
    total_chunks = embed_all_pending()

    # ── Step 4: Retrieve ─────────────────────────────────────────────────
    print("\n[4/4] Retrieving for a Dutch FinTech profile...")
    profile = {
        "industry":   "fintech",
        "country":    "NL",
        "activities": "payment services, lending, compliance reporting",
    }

    chunks = retrieve_relevant_regulations(
        profile,
        "AML and PSD2 obligations for payment companies",
        top_k=5,
    )

    print(f"\n✅ Retrieved {len(chunks)} relevant chunks")
    for i, chunk in enumerate(chunks, 1):
        title    = chunk.get("title", "")[:60]
        snippet  = (chunk.get("full_text") or "")[:120].replace("\n", " ")
        sim      = chunk.get("similarity")
        sim_str  = f" (sim={sim:.2f})" if sim is not None else ""
        print(f"\n📌 Chunk {i}{sim_str}: {title}")
        print(f"   {snippet}...")

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print(f"  New scraped: {new_count}   Relevant: {relevant}   Irrelevant: {irrelevant}")
    print(f"  Embedded chunks: {total_chunks}   Retrieved: {len(chunks)}")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    main()
