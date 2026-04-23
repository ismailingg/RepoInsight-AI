import os
import json
import hashlib
import time
from typing import List, Dict
import chromadb
import google.generativeai as genai
from backend.config import GOOGLE_API_KEY, EMBEDDING_MODEL, CHROMA_DB_PATH, EMBEDDING_BATCH_SIZE

# Initialize Google AI
genai.configure(api_key=GOOGLE_API_KEY)

# ChromaDB client (persistent storage)
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Constants
MAX_EMBEDDING_CHARS = 8000      # ~2000 tokens (1 token ≈ 4 chars for code)
CHECKPOINT_FILE     = "./data/embedding_checkpoint.json"
DELAY_BETWEEN_CALLS = 4.5       # seconds between API calls — stays under 15 RPM


# ── Checkpoint management ───────────────────────────────────────

def save_checkpoint(processed_ids: set):
    """Save checkpoint of already-embedded chunk IDs."""
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(list(processed_ids), f)


def load_checkpoint() -> set:
    """Load checkpoint to resume interrupted embedding."""
    if not os.path.exists(CHECKPOINT_FILE):
        return set()
    with open(CHECKPOINT_FILE, "r") as f:
        return set(json.load(f))


def clear_checkpoint():
    """Remove checkpoint file after successful completion."""
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        print("[CHECKPOINT] Cleared")


# ── Content deduplication ───────────────────────────────────────

def hash_content(content: str) -> str:
    """Generate hash of chunk content for deduplication."""
    return hashlib.md5(content.encode()).hexdigest()


def deduplicate_chunks(chunks: List[Dict]) -> tuple[List[Dict], int]:
    """
    Remove duplicate chunks (same content, different files).
    Returns: (unique_chunks, num_duplicates)
    """
    seen_hashes = {}
    unique_chunks = []

    for chunk in chunks:
        content_hash = hash_content(chunk["content"])

        if content_hash not in seen_hashes:
            seen_hashes[content_hash] = chunk["relative_path"]
            unique_chunks.append(chunk)
        else:
            original_file = seen_hashes[content_hash]
            print(f"[DEDUP] Skipped duplicate: {chunk['relative_path']} "
                  f"(same as {original_file})")

    duplicates = len(chunks) - len(unique_chunks)
    return unique_chunks, duplicates


# ── Embedding generation ────────────────────────────────────────

def truncate_content(content: str) -> str:
    """
    Truncate content to fit within embedding token limit.
    Keeps function signature + beginning of body.
    """
    if len(content) <= MAX_EMBEDDING_CHARS:
        return content

    truncated = content[:MAX_EMBEDDING_CHARS]
    print(f"[WARN] Truncated chunk from {len(content)} to {len(truncated)} chars")
    return truncated


def embed_single(text: str) -> List[float]:
    """
    Embed one text with automatic retry on rate limit.
    EMBEDDING_MODEL in .env already includes 'models/' prefix
    e.g. EMBEDDING_MODEL=models/gemini-embedding-001
    """
    max_retries = 5

    for attempt in range(max_retries):
        try:
            result = genai.embed_content(
                model=EMBEDDING_MODEL,        # already "models/gemini-embedding-001"
                content=text,
                task_type="retrieval_document"
            )
            return result["embedding"]

        except Exception as e:
            error_str = str(e)

            if "429" in error_str:
                # Rate limited — exponential backoff
                wait = (attempt + 1) * 20    # 20s, 40s, 60s, 80s, 100s
                print(f"\n  [RATE LIMIT] Quota hit. Waiting {wait}s "
                      f"(attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)

            elif "404" in error_str:
                # Model not found — no point retrying
                print(f"\n  [ERROR] Model '{EMBEDDING_MODEL}' not found.")
                print(f"  Fix EMBEDDING_MODEL in .env — must be one of:")
                print(f"    models/gemini-embedding-001")
                print(f"    models/gemini-embedding-2")
                raise

            else:
                # Unknown error — raise immediately
                raise

    raise RuntimeError(f"Failed to embed after {max_retries} retries")


def embed_batch(chunks: List[Dict]) -> List[List[float]]:
    """
    Embed chunks one-by-one with 4.5s delay between each call.
    Keeps requests at ~13/min, safely under the 15 RPM free tier limit.
    """
    embeddings = []

    for i, chunk in enumerate(chunks):
        text = truncate_content(chunk["content"])
        embedding = embed_single(text)
        embeddings.append(embedding)

        # Show progress within batch
        print(f"    [{i+1}/{len(chunks)}]", end="\r", flush=True)

        # Delay after every call except the last one in batch
        if i < len(chunks) - 1:
            time.sleep(DELAY_BETWEEN_CALLS)

    return embeddings


# ── ChromaDB storage ────────────────────────────────────────────

def get_or_create_collection(repo_url: str):
    """
    Get or create a ChromaDB collection for this repo.
    Collection name is a hash of the repo URL — prevents
    collisions between different repos in the same ChromaDB.
    """
    repo_hash = hashlib.md5(repo_url.encode()).hexdigest()[:16]
    collection_name = f"repo_{repo_hash}"

    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"repo_url": repo_url}
    )

    return collection


def store_embeddings(collection, chunks: List[Dict], embeddings: List[List[float]]):
    """Store chunk embeddings and metadata in ChromaDB."""
    ids       = [chunk["chunk_id"] for chunk in chunks]
    documents = [chunk["content"] for chunk in chunks]
    metadatas = [
        {
            "file":       chunk["relative_path"],
            "start_line": chunk["start_line"],
            "end_line":   chunk["end_line"],
            "language":   chunk["language"],
            "chunk_type": chunk["chunk_type"]
        }
        for chunk in chunks
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )


# ── Main ingestion pipeline ─────────────────────────────────────

def embed_and_store(chunks: List[Dict], repo_url: str) -> Dict:
    """
    Main Phase 3 entry point.

    Args:
        chunks:   List of chunks from Phase 2
        repo_url: GitHub repo URL (used for ChromaDB collection naming)

    Returns:
        Statistics dict
    """
    print(f"\n=== Phase 3: Embedding + Storage ===")
    print(f"Repository:       {repo_url}")
    print(f"Embedding model:  {EMBEDDING_MODEL}")

    # ── Step 1: Deduplicate ──────────────────────────────────────
    print("\n[1/4] Deduplicating chunks...")
    unique_chunks, num_duplicates = deduplicate_chunks(chunks)
    print(f"  ✓ {len(unique_chunks)} unique chunks ({num_duplicates} duplicates removed)")

    # ── Step 2: Load checkpoint ──────────────────────────────────
    print("\n[2/4] Checking for previous progress...")
    processed_ids = load_checkpoint()

    if processed_ids:
        unique_chunks = [c for c in unique_chunks if c["chunk_id"] not in processed_ids]
        print(f"  ✓ Resuming — {len(processed_ids)} already done, "
              f"{len(unique_chunks)} remaining")
    else:
        print(f"  ✓ Starting fresh")

    if not unique_chunks:
        print("\n✓ All chunks already embedded!")
        clear_checkpoint()
        return {
            "total_chunks":  len(chunks),
            "unique_chunks": len(chunks) - num_duplicates,
            "embedded":      0,
            "skipped":       len(processed_ids)
        }

    # ── Step 3: ChromaDB collection ─────────────────────────────
    print("\n[3/4] Preparing ChromaDB collection...")
    collection = get_or_create_collection(repo_url)
    print(f"  ✓ Collection: {collection.name}")

    # ── Step 4: Embed and store ──────────────────────────────────
    total_batches  = (len(unique_chunks) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
    estimated_mins = (len(unique_chunks) * DELAY_BETWEEN_CALLS) / 60

    print(f"\n[4/4] Embedding {len(unique_chunks)} chunks...")
    print(f"  Batch size:      {EMBEDDING_BATCH_SIZE} chunks")
    print(f"  Delay per call:  {DELAY_BETWEEN_CALLS}s (stays under 15 RPM)")
    print(f"  Estimated time:  ~{estimated_mins:.0f} minutes\n")

    batch_count    = 0
    embedded_count = 0

    for i in range(0, len(unique_chunks), EMBEDDING_BATCH_SIZE):
        batch       = unique_chunks[i:i + EMBEDDING_BATCH_SIZE]
        batch_count += 1

        print(f"  Batch {batch_count}/{total_batches} ({len(batch)} chunks)...", end=" ", flush=True)

        try:
            embeddings = embed_batch(batch)
            store_embeddings(collection, batch, embeddings)

            # Save checkpoint after every successful batch
            processed_ids.update(chunk["chunk_id"] for chunk in batch)
            save_checkpoint(processed_ids)

            embedded_count += len(batch)
            print(f"✓  [{embedded_count}/{len(unique_chunks)} done]")

        except Exception as e:
            print(f"✗ FAILED")
            print(f"\n[ERROR] Batch {batch_count} failed: {e}")
            print(f"[INFO]  Progress saved. Run again to resume.")
            return {
                "total_chunks":    len(chunks),
                "unique_chunks":   len(chunks) - num_duplicates,
                "embedded":        embedded_count,
                "failed_at_batch": batch_count,
                "error":           str(e)
            }

    # ── All done ─────────────────────────────────────────────────
    clear_checkpoint()

    print(f"\n✓ Phase 3 complete!")
    print(f"  Chunks embedded:     {embedded_count}")
    print(f"  ChromaDB collection: {collection.name}")

    return {
        "total_chunks":    len(chunks),
        "unique_chunks":   len(chunks) - num_duplicates,
        "embedded":        embedded_count,
        "collection_name": collection.name
    }