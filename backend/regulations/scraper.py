"""
Regulatory scraper — fetches updates from AFM, EBA, and EUR-Lex.

Ported from the working scraper_request.py at the project root.
Adds:
  - fetch_full_text(url) for retrieving the full text behind each link
  - save_to_db() to persist new items (deduplicated by URL)
"""

import sys
import os
import time
from datetime import datetime
from io import BytesIO

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client import get_client


# ---------------------------------------------------------------------------
# AFM — RSS feed (lxml handles malformed XML)
# ---------------------------------------------------------------------------

def fetch_afm():
    url = "https://www.afm.nl/rss/en/news"
    try:
        r = requests.get(url, headers={"User-Agent": "PROSPEX/1.0"}, timeout=15)

        # AFM RSS has HTML5-style attributes (e.g. async without value) — use recovering parser
        from lxml import etree
        parser = etree.XMLParser(recover=True)
        root   = etree.fromstring(r.content, parser=parser)

        items = root.findall(".//item") if root is not None else []

        # Fallback to BeautifulSoup if lxml found nothing
        if not items:
            soup  = BeautifulSoup(r.content, "xml")
            items = soup.find_all("item")
            results = []
            for item in items[:15]:
                results.append({
                    "source":  "AFM",
                    "title":   item.find("title").get_text(strip=True)       if item.find("title")       else "",
                    "url":     item.find("link").get_text(strip=True)        if item.find("link")        else "",
                    "date":    item.find("pubDate").get_text(strip=True)     if item.find("pubDate")     else "",
                    "summary": (item.find("description").get_text(strip=True)[:400]
                                if item.find("description") else ""),
                })
            print(f"   AFM: {len(results)} items (BeautifulSoup fallback)")
            return results

        results = []
        for item in items[:15]:
            def txt(tag):
                el = item.find(tag)
                return el.text.strip() if el is not None and el.text else ""
            results.append({
                "source":  "AFM",
                "title":   txt("title"),
                "url":     txt("link"),
                "date":    txt("pubDate"),
                "summary": txt("description")[:400],
            })
        print(f"   AFM: {len(results)} items")
        return results

    except Exception as e:
        print(f"   AFM failed: {e}")
        return []


# ---------------------------------------------------------------------------
# EBA — scrape /publications HTML
# ---------------------------------------------------------------------------

def fetch_eba():
    url = "https://www.eba.europa.eu/publications"
    try:
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=15,
        )
        soup     = BeautifulSoup(r.text, "html.parser")
        articles = soup.find_all("article")

        results = []
        for article in articles[:15]:
            title_tag = article.find(["h2", "h3", "h4", "a"])
            title     = title_tag.get_text(strip=True) if title_tag else ""
            link_tag  = article.find("a", href=True)
            link      = link_tag["href"] if link_tag else ""
            date_tag  = article.find("time")
            date      = date_tag.get_text(strip=True) if date_tag else ""

            if link and not link.startswith("http"):
                link = "https://www.eba.europa.eu" + link

            if title and len(title) > 10:
                results.append({
                    "source":  "EBA",
                    "title":   title,
                    "url":     link,
                    "date":    date,
                    "summary": "",
                })
        print(f"   EBA: {len(results)} items")
        return results

    except Exception as e:
        print(f"   EBA failed: {e}")
        return []


# ---------------------------------------------------------------------------
# EUR-Lex — SPARQL with retries + curated fallback
# ---------------------------------------------------------------------------

_CURATED_EUR_LEX = [
    {"source": "EUR-Lex", "title": "GDPR — General Data Protection Regulation (EU) 2016/679",
     "date": "2018-05-25", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679", "summary": ""},
    {"source": "EUR-Lex", "title": "PSD2 — Payment Services Directive (EU) 2015/2366",
     "date": "2018-01-13", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32015L2366", "summary": ""},
    {"source": "EUR-Lex", "title": "MiCA — Markets in Crypto-Assets Regulation (EU) 2023/1114",
     "date": "2023-06-09", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32023R1114", "summary": ""},
    {"source": "EUR-Lex", "title": "DORA — Digital Operational Resilience Act (EU) 2022/2554",
     "date": "2025-01-17", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022R2554", "summary": ""},
    {"source": "EUR-Lex", "title": "EU AI Act — Artificial Intelligence Act (EU) 2024/1689",
     "date": "2024-08-01", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689", "summary": ""},
    {"source": "EUR-Lex", "title": "AML — Anti-Money Laundering Regulation (EU) 2024/1624",
     "date": "2024-06-19", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1624", "summary": ""},
]


def fetch_eur_lex():
    endpoint = "https://publications.europa.eu/webapi/rdf/sparql"
    query = """
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT DISTINCT ?work ?title ?date WHERE {
        ?work cdm:work_date_document ?date .
        ?expr cdm:expression_belongs_to_work ?work .
        ?expr cdm:expression_title ?title .
        FILTER(lang(?title) = "en")
        FILTER(?date >= "2026-01-01"^^xsd:date)
        FILTER(contains(lcase(str(?title)), "financial"))
    }
    ORDER BY DESC(?date)
    LIMIT 15
    """

    for attempt in range(1, 4):
        try:
            r = requests.post(
                endpoint,
                data    = {"query": query, "format": "application/sparql-results+json"},
                headers = {"Accept": "application/sparql-results+json"},
                timeout = 60,
            )
            if r.status_code == 200:
                bindings = r.json()["results"]["bindings"]
                results = [{
                    "source":  "EUR-Lex",
                    "title":   b.get("title", {}).get("value", ""),
                    "date":    b.get("date",  {}).get("value", ""),
                    "url":     b.get("work",  {}).get("value", ""),
                    "summary": "",
                } for b in bindings]
                print(f"   EUR-Lex: {len(results)} items (SPARQL)")
                return results

        except requests.exceptions.ReadTimeout:
            if attempt < 3:
                time.sleep(attempt * 10)
        except Exception as e:
            print(f"   EUR-Lex SPARQL error: {e}")
            break

    print(f"   EUR-Lex: SPARQL timed out, using curated list ({len(_CURATED_EUR_LEX)} items)")
    return _CURATED_EUR_LEX


# ---------------------------------------------------------------------------
# Full-text fetcher
# ---------------------------------------------------------------------------

def fetch_full_text(url):
    """
    Retrieves the full text content from a URL.
    Handles HTML with BeautifulSoup and PDFs with pdfminer.
    Returns the text or None if it can't be fetched.
    """
    if not url:
        return None
    try:
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 PROSPEX/1.0"},
            timeout=20,
        )
        if r.status_code != 200:
            return None

        content_type = r.headers.get("Content-Type", "").lower()

        if "pdf" in content_type or url.lower().endswith(".pdf"):
            try:
                from pdfminer.high_level import extract_text
                text = extract_text(BytesIO(r.content))
                return text.strip() if text else None
            except Exception:
                return None

        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Collapse whitespace
        text = " ".join(text.split())
        return text[:30000] if text else None  # cap at 30k chars

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _existing_urls():
    """Returns set of URLs already in regulation_updates (for dedup)."""
    result = get_client().table("regulation_updates").select("url").execute()
    return {r["url"] for r in (result.data or []) if r.get("url")}


def _clean(s):
    """Strip NUL bytes and surrogate halves — Postgres rejects both."""
    if not s:
        return s
    if not isinstance(s, str):
        s = str(s)
    return s.replace("\x00", "").encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")


def save_to_db(items, fetch_text=True):
    """
    Inserts new items into regulation_updates, skipping URLs already present.
    Returns the count of newly inserted rows.
    """
    client     = get_client()
    seen       = _existing_urls()
    new_items  = [i for i in items if i.get("url") and i["url"] not in seen]

    print(f"\nSaving {len(new_items)} new items (skipping {len(items) - len(new_items)} duplicates)...")

    inserted = 0
    for item in new_items:
        full_text = fetch_full_text(item["url"]) if fetch_text else None
        if not full_text:
            full_text = (item.get("title") or "") + " " + (item.get("summary") or "")

        row = {
            "source":      _clean(item.get("source")),
            "title":       _clean(item.get("title")),
            "url":         item["url"],
            "date":        _clean(item.get("date")),
            "summary":     _clean(item.get("summary")),
            "full_text":   _clean(full_text),
            "is_relevant": None,  # set by filter.py
        }
        try:
            client.table("regulation_updates").insert(row).execute()
            inserted += 1
        except Exception as e:
            print(f"   ⚠️  Skipped: {item.get('title', '')[:50]} — {e}")

    print(f"✅ Inserted {inserted} new regulation records")
    return inserted


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_all(fetch_text=True):
    """Fetches from all sources and saves to the database. Returns new-row count."""
    print("\n" + "═" * 50)
    print("  Fetching regulatory feeds")
    print("═" * 50)

    items = []
    items.extend(fetch_afm())
    items.extend(fetch_eba())
    items.extend(fetch_eur_lex())

    print(f"\n   Total fetched: {len(items)}")
    return save_to_db(items, fetch_text=fetch_text)


if __name__ == "__main__":
    run_all()
