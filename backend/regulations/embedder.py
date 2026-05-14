"""
Chunks regulation full text and stores BGE embeddings in pgvector.

Each chunk becomes its own row in regulation_updates with the same source/title/url
metadata as the parent. This keeps similarity search simple — one cosine query
across all chunks of all regulations.

The original "parent" row (no embedding, full text intact) stays untouched
so we always know what was scraped originally.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client import get_client

_model = None


def _get_model():
    """Lazy-loads BGE. First call takes ~30s (downloads weights ~440 MB)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print("Loading BAAI/bge-base-en-v1.5 (first run downloads ~440 MB)...")
        _model = SentenceTransformer("BAAI/bge-base-en-v1.5")
        print("✅ Model loaded")
    return _model


def chunk_text(text, chunk_size=400, overlap=50):
    """
    Splits text into ~chunk_size word chunks with overlap between chunks.
    Word-based chunking is close enough to token-based for our purposes
    and avoids needing a tokenizer.
    """
    if not text:
        return []

    words = text.split()
    if len(words) <= chunk_size:
        return [text]

    chunks = []
    step   = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        if i + chunk_size >= len(words):
            break
    return chunks


def embed_regulation(regulation_id):
    """
    Chunks the regulation's full_text, embeds each chunk, and inserts
    each chunk as a new row in regulation_updates with embedding populated.
    Returns the number of chunks inserted.
    """
    client = get_client()

    result = (
        client.table("regulation_updates")
        .select("*")
        .eq("id", regulation_id)
        .single()
        .execute()
    )
    if not result.data:
        return 0

    row = result.data
    text = row.get("full_text") or row.get("summary") or row.get("title") or ""

    chunks = chunk_text(text)
    if not chunks:
        return 0

    model      = _get_model()
    embeddings = model.encode(chunks, normalize_embeddings=True, show_progress_bar=False)

    def clean(s):
        if not s:
            return s
        return str(s).replace("\x00", "").encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")

    rows_to_insert = []
    for chunk, embedding in zip(chunks, embeddings):
        rows_to_insert.append({
            "source":      clean(row.get("source")),
            "title":       clean(row.get("title")),
            "url":         row.get("url") + f"#chunk-{len(rows_to_insert)}",
            "date":        clean(row.get("date")),
            "summary":     clean(row.get("summary")),
            "full_text":   clean(chunk),
            "embedding":   embedding.tolist(),
            "is_relevant": True,
        })

    for r in rows_to_insert:
        try:
            client.table("regulation_updates").insert(r).execute()
        except Exception as e:
            # Ignore unique-violation collisions on URL fragment
            if "duplicate" not in str(e).lower():
                print(f"   ⚠️  Insert error: {e}")

    return len(rows_to_insert)


def embed_all_pending():
    """
    Embeds every relevant regulation that hasn't been embedded yet.
    Identifies "parent" rows by: is_relevant = True AND embedding IS NULL
    AND url does NOT contain '#chunk-'.
    Shows a tqdm progress bar.
    """
    client = get_client()

    result = (
        client.table("regulation_updates")
        .select("id, url")
        .eq("is_relevant", True)
        .is_("embedding", "null")
        .execute()
    )
    parents = [r for r in (result.data or []) if "#chunk-" not in (r.get("url") or "")]

    if not parents:
        print("No relevant regulations pending embedding.")
        return 0

    print(f"\nEmbedding {len(parents)} regulations (first run downloads model)...")

    try:
        from tqdm import tqdm
        iterator = tqdm(parents, desc="Embedding")
    except ImportError:
        iterator = parents

    total_chunks = 0
    for parent in iterator:
        chunks = embed_regulation(parent["id"])
        total_chunks += chunks

    print(f"✅ Embedded {len(parents)} regulations → {total_chunks} chunks")
    return total_chunks


if __name__ == "__main__":
    embed_all_pending()
