# Hybrid Retrieval
import os
import re
import hashlib
from typing import List, Dict, Optional
import chromadb
import google.generativeai as genai
from backend.config import (
    GOOGLE_API_KEY, EMBEDDING_MODEL,
    CHROMA_DB_PATH
)

# Initialize
genai.configure(api_key=GOOGLE_API_KEY)
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Constants
SEMANTIC_TOP_K    = 10   # how many chunks to fetch from ChromaDB
GREP_MAX_RESULTS  = 15   # max grep results to avoid common-name flood
MIN_SCORE         = 0.0  # minimum similarity score (0 = keep everything)

# File priority for grep ranking
PRIORITY_FILES = ["app.py", "main.py", "index.js", "__init__.py",
                  "views.py", "models.py", "routes.py", "middleware.py"]


# ── Semantic search ─────────────────────────────────────────────

def embed_question(question: str) -> List[float]:
    """Convert question to vector using same model as chunks."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=question,
        task_type="retrieval_query"   # different task type for queries
    )
    return result["embedding"]


def semantic_search(question: str, collection) -> List[Dict]:
    """
    Embed the question and find top-K similar chunks in ChromaDB.
    Returns list of chunks with similarity scores.
    """
    question_vector = embed_question(question)

    results = collection.query(
        query_embeddings=[question_vector],
        n_results=SEMANTIC_TOP_K,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    if not results["ids"][0]:
        return chunks

    for i in range(len(results["ids"][0])):
        # ChromaDB returns distance (lower = more similar)
        # Convert to similarity score (higher = more similar)
        distance   = results["distances"][0][i]
        similarity = 1 - distance

        chunks.append({
            "chunk_id":      results["ids"][0][i],
            "content":       results["documents"][0][i],
            "file":          results["metadatas"][0][i]["file"],
            "start_line":    results["metadatas"][0][i]["start_line"],
            "end_line":      results["metadatas"][0][i]["end_line"],
            "language":      results["metadatas"][0][i]["language"],
            "chunk_type":    results["metadatas"][0][i]["chunk_type"],
            "similarity":    round(similarity, 4),
            "source":        "semantic"
        })

    return chunks


# ── Grep search ─────────────────────────────────────────────────

def extract_identifiers(question: str) -> List[str]:
    """
    Extract only REAL code identifiers — not plain English words.
    Only matches: snake_case, UPPER_CASE, camelCase, PascalCase
    with at least one underscore OR capital letter pattern.
    """
    identifiers = []

    # snake_case with underscore (real identifiers): verify_token, push_appctx
    # Requires at least one underscore to avoid plain English words
    snake_case = re.findall(r'\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b', question)
    identifiers.extend(snake_case)

    # UPPER_CASE constants: MAX_RETRIES, SECRET_KEY
    upper_case = re.findall(r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b', question)
    identifiers.extend(upper_case)

    # PascalCase class names: AuthManager, UserService, AppContext
    pascal_case = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-zA-Z]*)+\b', question)
    identifiers.extend(pascal_case)

    # Deduplicate
    seen = set()
    unique = []
    for i in identifiers:
        if i not in seen:
            seen.add(i)
            unique.append(i)

    return unique

    
def file_importance_score(filepath: str) -> int:
    """Higher score = more important file = ranked higher in grep results."""
    name = os.path.basename(filepath).lower()
    if any(p in name for p in PRIORITY_FILES):
        return 2
    if "test" in name:
        return 0
    return 1


def grep_search(identifiers: List[str], repo_path: str,
                all_chunks: List[Dict]) -> List[Dict]:
    """
    Search for exact identifier matches across raw repo files.
    Falls back to searching chunk content if repo_path not available.

    Returns list of matching chunks with grep source tag.
    """
    if not identifiers:
        return []

    matched_chunks = []
    seen_ids = set()

    for identifier in identifiers:
        matches_for_id = []

        # Search through chunk content (works without raw files)
        for chunk in all_chunks:
            if identifier in chunk.get("content", ""):
                chunk_id = chunk.get("chunk_id", "")
                if chunk_id not in seen_ids:
                    seen_ids.add(chunk_id)
                    matches_for_id.append({
                        "chunk_id":   chunk_id,
                        "content":    chunk["content"],
                        "file":       chunk["relative_path"],
                        "start_line": chunk["start_line"],
                        "end_line":   chunk["end_line"],
                        "language":   chunk["language"],
                        "chunk_type": chunk["chunk_type"],
                        "similarity": 0.5,      # neutral score for grep results
                        "source":     "grep",
                        "matched_identifier": identifier
                    })

        # Sort by file importance (entry points rank higher)
        matches_for_id.sort(
            key=lambda c: file_importance_score(c["file"]),
            reverse=True
        )

        # Cap per identifier to avoid flooding from common names
        matched_chunks.extend(matches_for_id[:GREP_MAX_RESULTS])

    return matched_chunks


# ── Merge results ───────────────────────────────────────────────

def merge_results(semantic_chunks: List[Dict],
                  grep_chunks: List[Dict]) -> List[Dict]:
    """
    Merge semantic and grep results.
    - Deduplicate by chunk_id
    - If same chunk found by both, mark source as "both" and boost score
    - Sort by similarity score descending
    """
    merged = {}

    # Add semantic results first
    for chunk in semantic_chunks:
        merged[chunk["chunk_id"]] = chunk

    # Add grep results — boost score if already found semantically
    for chunk in grep_chunks:
        cid = chunk["chunk_id"]
        if cid in merged:
            # Found by both — boost its score and mark source
            merged[cid]["similarity"] = min(1.0, merged[cid]["similarity"] + 0.1)
            merged[cid]["source"] = "both"
        else:
            merged[cid] = chunk

    # Sort by similarity descending
    sorted_chunks = sorted(
        merged.values(),
        key=lambda c: c["similarity"],
        reverse=True
    )

    return sorted_chunks


# ── Stale chunk validation ──────────────────────────────────────

def validate_chunks(chunks: List[Dict], repo_path: Optional[str] = None) -> List[Dict]:
    """
    Validate that chunks reference files that still exist.
    Flags stale chunks if repo_path is provided.
    """
    if not repo_path:
        return chunks

    valid = []
    for chunk in chunks:
        full_path = os.path.join(repo_path, chunk["file"])
        if os.path.exists(full_path):
            valid.append(chunk)
        else:
            print(f"[WARN] Stale chunk — file no longer exists: {chunk['file']}")

    return valid


# ── Main retrieval entry point ──────────────────────────────────

def retrieve(question: str, repo_url: str,
             all_chunks: List[Dict] = None,
             repo_path: str = None) -> Dict:
    """
    Main Phase 4 entry point. Runs hybrid retrieval.

    Args:
        question:   User's natural language question
        repo_url:   GitHub URL (to find the right ChromaDB collection)
        all_chunks: All chunks from Phase 2 (for grep search)
        repo_path:  Path to cloned repo (for stale validation)

    Returns:
        Dict with retrieved chunks + search metadata
    """
    print(f"\n=== Phase 4: Hybrid Retrieval ===")
    print(f"Question: {question}")

    # Get ChromaDB collection
    repo_hash  = hashlib.md5(repo_url.encode()).hexdigest()[:16]
    collection = chroma_client.get_collection(f"repo_{repo_hash}")

    # ── Semantic search ──────────────────────────────────────────
    print("\n[1/3] Semantic search...")
    semantic_chunks = semantic_search(question, collection)

    if not semantic_chunks:
        print("  [WARN] Zero semantic results — falling back to grep only")
    else:
        print(f"  ✓ {len(semantic_chunks)} chunks found")
        for c in semantic_chunks[:3]:   # show top 3
            print(f"    {c['file']}:{c['start_line']} "
                  f"(similarity: {c['similarity']})")

    # ── Grep search ──────────────────────────────────────────────
    print("\n[2/3] Grep search...")
    identifiers = extract_identifiers(question)

    if identifiers:
        print(f"  Identifiers found: {identifiers}")
        grep_chunks = grep_search(identifiers, repo_path, all_chunks or [])
        print(f"  ✓ {len(grep_chunks)} chunks found")
    else:
        print("  No specific identifiers found — skipping grep")
        grep_chunks = []

    # ── Merge ────────────────────────────────────────────────────
    print("\n[3/3] Merging results...")
    merged = merge_results(semantic_chunks, grep_chunks)

    # Validate stale chunks
    merged = validate_chunks(merged, repo_path)

    # Summary
    both_count     = sum(1 for c in merged if c["source"] == "both")
    semantic_count = sum(1 for c in merged if c["source"] == "semantic")
    grep_count     = sum(1 for c in merged if c["source"] == "grep")

    print(f"  ✓ {len(merged)} total chunks")
    print(f"    Semantic only: {semantic_count}")
    print(f"    Grep only:     {grep_count}")
    print(f"    Found by both: {both_count} (score boosted)")

    return {
        "question":    question,
        "chunks":      merged,
        "identifiers": identifiers,
        "stats": {
            "semantic": semantic_count,
            "grep":     grep_count,
            "both":     both_count,
            "total":    len(merged)
        }
    }