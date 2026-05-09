import os
import re
import hashlib
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from backend.config import QDRANT_URL, QDRANT_API_KEY

# ── Qdrant client (singleton) ────────────────────────────────────
if QDRANT_URL:
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
else:
    from backend.config import QDRANT_LOCAL_PATH
    qdrant_client = QdrantClient(path=QDRANT_LOCAL_PATH)

SEMANTIC_TOP_K   = 10
GREP_MAX_RESULTS = 15

PRIORITY_FILES = ["app.py", "main.py", "index.js", "__init__.py",
                  "views.py", "models.py", "routes.py", "middleware.py"]


def get_collection_name(repo_url: str, user_id: str = "") -> str:
    combined  = f"{user_id}:{repo_url}"
    repo_hash = hashlib.md5(combined.encode()).hexdigest()[:16]
    return f"repo_{repo_hash}"


def embed_question(question: str, provider: str, api_key: str, model: str) -> List[float]:
    from backend.utils.embedding import embed_query
    return embed_query(question, provider, api_key, model)


def semantic_search(
    question:        str,
    collection_name: str,
    provider:        str,
    api_key:         str,
    model:           str
) -> List[Dict]:
    question_vector = embed_question(question, provider, api_key, model)

    results = qdrant_client.search(
        collection_name = collection_name,
        query_vector    = question_vector,
        limit           = SEMANTIC_TOP_K,
        with_payload    = True
    )

    chunks = []
    for hit in results:
        payload    = hit.payload
        similarity = hit.score  # Qdrant cosine score is already 0-1
        chunks.append({
            "chunk_id":   payload.get("chunk_id",   hit.id),
            "content":    payload.get("content",    ""),
            "file":       payload.get("file",       ""),
            "start_line": payload.get("start_line", 0),
            "end_line":   payload.get("end_line",   0),
            "language":   payload.get("language",   ""),
            "chunk_type": payload.get("chunk_type", ""),
            "similarity": round(similarity, 4),
            "source":     "semantic"
        })

    return chunks


def extract_identifiers(question: str) -> List[str]:
    identifiers = []
    identifiers.extend(re.findall(r'\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b', question))
    identifiers.extend(re.findall(r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b', question))
    identifiers.extend(re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-zA-Z]*)+\b', question))

    seen   = set()
    unique = []
    for i in identifiers:
        if i not in seen:
            seen.add(i)
            unique.append(i)
    return unique


def file_importance_score(filepath: str) -> int:
    name = os.path.basename(filepath).lower()
    if any(p in name for p in PRIORITY_FILES): return 2
    if "test" in name:                          return 0
    return 1


def grep_search(identifiers: List[str], all_chunks: List[Dict]) -> List[Dict]:
    if not identifiers:
        return []

    matched_chunks = []
    seen_ids       = set()

    for identifier in identifiers:
        matches_for_id = []
        for chunk in all_chunks:
            if identifier in chunk.get("content", ""):
                chunk_id = chunk.get("chunk_id", "")
                if chunk_id not in seen_ids:
                    seen_ids.add(chunk_id)
                    matches_for_id.append({
                        "chunk_id":           chunk_id,
                        "content":            chunk["content"],
                        "file":               chunk["relative_path"],
                        "start_line":         chunk["start_line"],
                        "end_line":           chunk["end_line"],
                        "language":           chunk["language"],
                        "chunk_type":         chunk["chunk_type"],
                        "similarity":         0.5,
                        "source":             "grep",
                        "matched_identifier": identifier
                    })

        matches_for_id.sort(key=lambda c: file_importance_score(c["file"]), reverse=True)
        matched_chunks.extend(matches_for_id[:GREP_MAX_RESULTS])

    return matched_chunks


def merge_results(semantic_chunks: List[Dict], grep_chunks: List[Dict]) -> List[Dict]:
    merged = {}

    for chunk in semantic_chunks:
        merged[chunk["chunk_id"]] = chunk

    for chunk in grep_chunks:
        cid = chunk["chunk_id"]
        if cid in merged:
            merged[cid]["similarity"] = min(1.0, merged[cid]["similarity"] + 0.1)
            merged[cid]["source"]     = "both"
        else:
            merged[cid] = chunk

    return sorted(merged.values(), key=lambda c: c["similarity"], reverse=True)


def validate_chunks(chunks: List[Dict], repo_path: Optional[str] = None) -> List[Dict]:
    if not repo_path:
        return chunks
    valid = []
    for chunk in chunks:
        full_path = os.path.join(repo_path, chunk["file"])
        if os.path.exists(full_path):
            valid.append(chunk)
        else:
            print(f"[WARN] Stale chunk — file gone: {chunk['file']}")
    return valid


def retrieve(
    question:   str,
    repo_url:   str,
    all_chunks: List[Dict],
    provider:   str,
    api_key:    str,
    model:      str  = None,
    repo_path:  str  = None,
    user_id:    str  = ""
) -> Dict:
    """
    Main Phase 4 entry point — Hybrid semantic + grep retrieval using Qdrant.
    """
    from backend.utils.embedding import DEFAULT_EMBEDDING_MODELS
    model = model or DEFAULT_EMBEDDING_MODELS.get(provider, "models/gemini-embedding-001")

    print(f"\n=== Phase 4: Hybrid Retrieval ===")
    print(f"Question: {question}")

    collection_name = get_collection_name(repo_url, user_id)

    # Semantic search
    print("\n[1/3] Semantic search...")
    semantic_chunks = semantic_search(question, collection_name, provider, api_key, model)
    if not semantic_chunks:
        print("  [WARN] Zero semantic results — falling back to grep only")
    else:
        print(f"  ✓ {len(semantic_chunks)} chunks found")
        for c in semantic_chunks[:3]:
            print(f"    {c['file']}:{c['start_line']} (similarity: {c['similarity']})")

    # Grep search
    print("\n[2/3] Grep search...")
    identifiers = extract_identifiers(question)
    if identifiers:
        print(f"  Identifiers found: {identifiers}")
        grep_chunks = grep_search(identifiers, all_chunks or [])
        print(f"  ✓ {len(grep_chunks)} chunks found")
    else:
        print("  No specific identifiers — skipping grep")
        grep_chunks = []

    # Merge
    print("\n[3/3] Merging results...")
    merged = merge_results(semantic_chunks, grep_chunks)
    merged = validate_chunks(merged, repo_path)

    both_count     = sum(1 for c in merged if c["source"] == "both")
    semantic_count = sum(1 for c in merged if c["source"] == "semantic")
    grep_count     = sum(1 for c in merged if c["source"] == "grep")

    print(f"  ✓ {len(merged)} total chunks")
    print(f"    Semantic only: {semantic_count}")
    print(f"    Grep only:     {grep_count}")
    print(f"    Found by both: {both_count}")

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