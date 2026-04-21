import os
import json
import hashlib
import time
from typing import List, Dict
import chromadb
from chromadb.config import Settings
import google.generativeai as genai
from backend.config import GOOGLE_API_KEY, EMBEDDING_MODEL, CHROMA_DB_PATH, EMBEDDING_BATCH_SIZE

# Initialize Google AI
genai.configure(api_key=GOOGLE_API_KEY)

# ChromaDB client (persistent storage)
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Constants
MAX_EMBEDDING_TOKENS = 2000  # Google's limit
CHECKPOINT_FILE = "./data/embedding_checkpoint.json"


# ── Checkpoint management ───────────────────────────────────────

def save_checkpoint(processed_ids: set):
    """Save checkpoint of already-embedded chunk IDs."""
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(list(processed_ids), f)
    print(f"[CHECKPOINT] Saved {len(processed_ids)} processed chunks")


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

def truncate_content(content: str, max_tokens: int = MAX_EMBEDDING_TOKENS) -> str:
    """
    Truncate content to fit within token limit.
    Rough estimate: 1 token ≈ 4 characters for code.
    """
    max_chars = max_tokens * 4
    if len(content) <= max_chars:
        return content
    
    # Keep function signature + beginning of body
    truncated = content[:max_chars]
    print(f"[WARN] Truncated chunk from {len(content)} to {len(truncated)} chars")
    return truncated


def embed_batch(chunks: List[Dict]) -> List[List[float]]:
    """
    Embed a batch of chunks using Google's text-embedding-004.
    Returns list of 768-dimensional vectors.
    """
    # Prepare content for embedding
    texts = [truncate_content(chunk["content"]) for chunk in chunks]
    
    try:
        # Call Google Embedding API
        result = genai.embed_content(
            model=f"models/{EMBEDDING_MODEL}",
            content=texts,
            task_type="retrieval_document"  # optimized for search
        )
        
        # Extract embeddings
        if isinstance(result, dict) and "embedding" in result:
            # Single text response
            return [result["embedding"]]
        else:
            # Batch response
            return result["embedding"] if "embedding" in result else []
            
    except Exception as e:
        print(f"[ERROR] Embedding API failed: {e}")
        raise


# ── ChromaDB storage ────────────────────────────────────────────

def get_or_create_collection(repo_url: str):
    """
    Get or create a ChromaDB collection for this repo.
    Collection name is a hash of the repo URL to avoid collisions.
    """
    # Generate unique collection name from repo URL
    repo_hash = hashlib.md5(repo_url.encode()).hexdigest()[:16]
    collection_name = f"repo_{repo_hash}"
    
    # Get or create collection
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"repo_url": repo_url}
    )
    
    return collection


def store_embeddings(collection, chunks: List[Dict], embeddings: List[List[float]]):
    """
    Store chunk embeddings and metadata in ChromaDB.
    """
    # Prepare data for ChromaDB
    ids = [chunk["chunk_id"] for chunk in chunks]
    documents = [chunk["content"] for chunk in chunks]
    metadatas = [
        {
            "file": chunk["relative_path"],
            "start_line": chunk["start_line"],
            "end_line": chunk["end_line"],
            "language": chunk["language"],
            "chunk_type": chunk["chunk_type"]
        }
        for chunk in chunks
    ]
    
    # Store in ChromaDB
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
        chunks: List of chunks from Phase 2
        repo_url: GitHub repo URL (for collection naming)
    
    Returns:
        Statistics dict
    """
    print(f"\n=== Phase 3: Embedding + Storage ===")
    print(f"Repository: {repo_url}")
    
    # Step 1: Deduplicate chunks
    print("\n[1/4] Deduplicating chunks...")
    unique_chunks, num_duplicates = deduplicate_chunks(chunks)
    print(f"  ✓ {len(unique_chunks)} unique chunks ({num_duplicates} duplicates removed)")
    
    # Step 2: Load checkpoint
    print("\n[2/4] Checking for previous progress...")
    processed_ids = load_checkpoint()
    if processed_ids:
        print(f"  ✓ Found checkpoint with {len(processed_ids)} already processed")
        unique_chunks = [c for c in unique_chunks if c["chunk_id"] not in processed_ids]
        print(f"  ✓ {len(unique_chunks)} chunks remaining")
    else:
        print(f"  ✓ Starting fresh")
    
    if not unique_chunks:
        print("\n✓ All chunks already embedded!")
        clear_checkpoint()
        return {
            "total_chunks": len(chunks),
            "unique_chunks": len(chunks) - num_duplicates,
            "embedded": 0,
            "skipped": len(processed_ids)
        }
    
    # Step 3: Get ChromaDB collection
    print("\n[3/4] Preparing ChromaDB collection...")
    collection = get_or_create_collection(repo_url)
    print(f"  ✓ Collection: {collection.name}")
    
    # Step 4: Batch embed and store
    print(f"\n[4/4] Embedding {len(unique_chunks)} chunks (batch size: {EMBEDDING_BATCH_SIZE})...")
    
    batch_count = 0
    embedded_count = 0
    
    for i in range(0, len(unique_chunks), EMBEDDING_BATCH_SIZE):
        batch = unique_chunks[i:i + EMBEDDING_BATCH_SIZE]
        batch_count += 1
        
        try:
            # Generate embeddings
            print(f"  Batch {batch_count}/{(len(unique_chunks) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE} "
                  f"({len(batch)} chunks)...", end=" ")
            
            embeddings = embed_batch(batch)
            
            # Store in ChromaDB
            store_embeddings(collection, batch, embeddings)
            
            # Update checkpoint
            processed_ids.update(chunk["chunk_id"] for chunk in batch)
            save_checkpoint(processed_ids)
            
            embedded_count += len(batch)
            print("✓")
            
            # Rate limiting (Google free tier: 15 req/min)
            if batch_count % 10 == 0:
                print("  [Rate limiting] Pausing 5 seconds...")
                time.sleep(5)
            else:
                time.sleep(0.5)  # Small delay between batches
            
        except Exception as e:
            print(f"✗ FAILED")
            print(f"[ERROR] Batch {batch_count} failed: {e}")
            print(f"[INFO] Progress saved. Run again to resume from checkpoint.")
            return {
                "total_chunks": len(chunks),
                "unique_chunks": len(chunks) - num_duplicates,
                "embedded": embedded_count,
                "failed_at_batch": batch_count,
                "error": str(e)
            }
    
    # Success - clear checkpoint
    clear_checkpoint()
    
    print(f"\n✓ Embedding complete!")
    print(f"  Total chunks processed: {embedded_count}")
    print(f"  ChromaDB collection: {collection.name}")
    
    return {
        "total_chunks": len(chunks),
        "unique_chunks": len(chunks) - num_duplicates,
        "embedded": embedded_count,
        "collection_name": collection.name
    }