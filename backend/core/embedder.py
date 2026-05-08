import os
import json
import hashlib
import time
from typing import List, Dict
import chromadb
from backend.config import CHROMA_DB_PATH, EMBEDDING_BATCH_SIZE

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

MAX_EMBEDDING_CHARS = 8000
CHECKPOINT_FILE     = "./data/embedding_checkpoint.json"
DELAY_BETWEEN_CALLS = 4.5


def save_checkpoint(processed_ids: set):
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(list(processed_ids), f)


def load_checkpoint() -> set:
    if not os.path.exists(CHECKPOINT_FILE):
        return set()
    with open(CHECKPOINT_FILE, "r") as f:
        return set(json.load(f))


def clear_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        print("[CHECKPOINT] Cleared")


def hash_content(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()


def deduplicate_chunks(chunks: List[Dict]) -> tuple[List[Dict], int]:
    seen_hashes = {}
    unique_chunks = []
    for chunk in chunks:
        content_hash = hash_content(chunk["content"])
        if content_hash not in seen_hashes:
            seen_hashes[content_hash] = chunk["relative_path"]
            unique_chunks.append(chunk)
        else:
            print(f"[DEDUP] Skipped duplicate: {chunk['relative_path']} "
                  f"(same as {seen_hashes[content_hash]})")
    duplicates = len(chunks) - len(unique_chunks)
    return unique_chunks, duplicates


def truncate_content(content: str) -> str:
    if len(content) <= MAX_EMBEDDING_CHARS:
        return content
    print(f"[WARN] Truncated chunk from {len(content)} to {MAX_EMBEDDING_CHARS} chars")
    return content[:MAX_EMBEDDING_CHARS]


def embed_single(text: str, provider: str, api_key: str, model: str) -> List[float]:
    from backend.utils.embedding import embed_text
    max_retries = 5
    for attempt in range(max_retries):
        try:
            return embed_text(text, provider, api_key, model)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                wait = (attempt + 1) * 20
                print(f"\n  [RATE LIMIT] Waiting {wait}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
            elif "404" in error_str:
                print(f"\n  [ERROR] Model not found: {model}")
                raise
            else:
                raise
    raise RuntimeError(f"Failed to embed after {max_retries} retries")


def embed_batch(chunks: List[Dict], provider: str, api_key: str, model: str) -> List[List[float]]:
    embeddings = []
    for i, chunk in enumerate(chunks):
        text = truncate_content(chunk["content"])
        if not text or not text.strip():
            print(f"\n  [SKIP] Empty chunk: {chunk['relative_path']} line {chunk['start_line']}")
            text = f"# empty chunk from {chunk['relative_path']}"
        embedding = embed_single(text, provider, api_key, model)
        embeddings.append(embedding)
        print(f"    [{i+1}/{len(chunks)}]", end="\r", flush=True)
        if i < len(chunks) - 1:
            time.sleep(DELAY_BETWEEN_CALLS)
    return embeddings


def get_or_create_collection(repo_url: str, user_id: str = ""):
    combined = f"{user_id}:{repo_url}"
    repo_hash = hashlib.md5(combined.encode()).hexdigest()[:16]
    collection_name = f"repo_{repo_hash}"


def store_embeddings(collection, chunks: List[Dict], embeddings: List[List[float]]):
    collection.add(
        ids       = [c["chunk_id"]      for c in chunks],
        embeddings= embeddings,
        documents = [c["content"]       for c in chunks],
        metadatas = [{
            "file":       c["relative_path"],
            "start_line": c["start_line"],
            "end_line":   c["end_line"],
            "language":   c["language"],
            "chunk_type": c["chunk_type"]
        } for c in chunks]
    )


def embed_and_store(
    chunks:   List[Dict],
    repo_url: str,
    provider: str,
    api_key:  str,
    model:    str = None,
    user_id=""
) -> Dict:
    from backend.utils.embedding import DEFAULT_EMBEDDING_MODELS
    model = model or DEFAULT_EMBEDDING_MODELS.get(provider, "models/gemini-embedding-001")

    print(f"\n=== Phase 3: Embedding + Storage ===")
    print(f"Repository: {repo_url}")
    print(f"Provider:   {provider} / {model}")

    print("\n[1/4] Deduplicating chunks...")
    unique_chunks, num_duplicates = deduplicate_chunks(chunks)
    print(f"  ✓ {len(unique_chunks)} unique ({num_duplicates} duplicates removed)")

    print("\n[2/4] Checking checkpoint...")
    processed_ids = load_checkpoint()
    if processed_ids:
        unique_chunks = [c for c in unique_chunks if c["chunk_id"] not in processed_ids]
        print(f"  ✓ Resuming — {len(processed_ids)} done, {len(unique_chunks)} remaining")
    else:
        print(f"  ✓ Starting fresh")

    if not unique_chunks:
        print("\n✓ All chunks already embedded!")
        clear_checkpoint()
        return {"total_chunks": len(chunks), "unique_chunks": len(chunks)-num_duplicates, "embedded": 0}

    print("\n[3/4] Preparing ChromaDB collection...")
    collection = get_or_create_collection(repo_url, user_id)
    print(f"  ✓ Collection: {collection.name}")

    total_batches  = (len(unique_chunks) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
    estimated_mins = (len(unique_chunks) * DELAY_BETWEEN_CALLS) / 60
    print(f"\n[4/4] Embedding {len(unique_chunks)} chunks (~{estimated_mins:.0f} min)...\n")

    batch_count = 0
    embedded_count = 0

    for i in range(0, len(unique_chunks), EMBEDDING_BATCH_SIZE):
        batch = unique_chunks[i:i + EMBEDDING_BATCH_SIZE]
        batch_count += 1
        print(f"  Batch {batch_count}/{total_batches} ({len(batch)} chunks)...", end=" ", flush=True)
        try:
            embeddings = embed_batch(batch, provider, api_key, model)
            store_embeddings(collection, batch, embeddings)
            processed_ids.update(c["chunk_id"] for c in batch)
            save_checkpoint(processed_ids)
            embedded_count += len(batch)
            print(f"✓  [{embedded_count}/{len(unique_chunks)} done]")
        except Exception as e:
            print(f"✗ FAILED\n[ERROR] {e}\n[INFO] Progress saved.")
            return {
                "total_chunks": len(chunks), "unique_chunks": len(chunks)-num_duplicates,
                "embedded": embedded_count, "error": str(e)
            }

    clear_checkpoint()
    print(f"\n✓ Phase 3 complete! Collection: {collection.name}")
    return {
        "total_chunks":    len(chunks),
        "unique_chunks":   len(chunks) - num_duplicates,
        "embedded":        embedded_count,
        "collection_name": collection.name
    }