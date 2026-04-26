import time
from typing import List, Dict, Tuple
import google.generativeai as genai
from backend.config import GOOGLE_API_KEY, GEMINI_MODEL

# Initialize Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

# Constants
FIND_ALL_THRESHOLD  = 0.45   # minimum similarity for FIND_ALL path
EXPLAIN_TOP_N       = 3      # how many chunks to keep for EXPLAIN path
MIN_RERANK_SCORE    = 5      # minimum Gemini score (1-10) to keep a chunk
LOWERED_THRESHOLD   = 3      # fallback if fewer than 3 chunks score above 5


# ── Intent Detection ────────────────────────────────────────────

def detect_intent(question: str) -> str:
    """
    Ask Gemini to classify the question as EXPLAIN or FIND_ALL.

    EXPLAIN  → "how does X work?", "what does X do?", "explain X"
    FIND_ALL → "where is X used?", "list all places X appears", "find X"

    Returns: "EXPLAIN" or "FIND_ALL"
    """
    prompt = f"""Classify this developer question into exactly one category:

EXPLAIN  - The user wants to understand how something works, what something does,
           or wants a conceptual explanation.
           Examples: "how does authentication work?", "what does verify_token do?",
                     "explain the request lifecycle"

FIND_ALL - The user wants to locate every place something appears, find all usages,
           or get a complete list of occurrences.
           Examples: "where is push_appctx used?", "find all places MAX_RETRIES appears",
                     "list every file that imports auth"

Question: "{question}"

Rules:
- If the question is ambiguous or asks both how AND where, answer FIND_ALL
- Reply with ONLY the single word: EXPLAIN or FIND_ALL
- No explanation, no punctuation, just the word"""

    try:
        response = model.generate_content(prompt)
        intent = response.text.strip().upper()

        # Validate response
        if intent not in ("EXPLAIN", "FIND_ALL"):
            print(f"  [WARN] Unexpected intent response: '{intent}' — defaulting to FIND_ALL")
            return "FIND_ALL"

        return intent

    except Exception as e:
        print(f"  [WARN] Intent detection failed: {e} — defaulting to FIND_ALL")
        return "FIND_ALL"   # safer to over-return than under-return


# ── Re-ranking (EXPLAIN path only) ─────────────────────────────

def build_rerank_prompt(question: str, chunks: List[Dict]) -> str:
    """Build the prompt that asks Gemini to score each chunk."""

    chunks_text = ""
    for i, chunk in enumerate(chunks):
        chunks_text += f"""
CHUNK {i+1}:
File: {chunk['file']} (lines {chunk['start_line']}-{chunk['end_line']})
Type: {chunk['chunk_type']}
Content:
{chunk['content'][:500]}
---"""

    return f"""You are a code search re-ranker. Score each chunk for relevance to the question.

Question: "{question}"

{chunks_text}

Score each chunk from 1-10 where:
10 = directly answers the question
7  = highly relevant, contains important context  
5  = somewhat relevant
3  = loosely related
1  = not relevant at all

Reply in this EXACT format, one line per chunk, nothing else:
CHUNK 1: <score>
CHUNK 2: <score>
CHUNK 3: <score>
(continue for all {len(chunks)} chunks)"""


def parse_rerank_scores(response_text: str, num_chunks: int) -> List[int]:
    """
    Parse Gemini's scoring response into a list of integer scores.
    Returns list of scores, one per chunk.
    Falls back to 5 (neutral) for any unparseable line.
    """
    import re
    scores = [5] * num_chunks   # default neutral score

    lines = response_text.strip().split("\n")
    for line in lines:
        # Match "CHUNK N: score"
        match = re.search(r'CHUNK\s+(\d+):\s*(\d+)', line, re.IGNORECASE)
        if match:
            chunk_idx  = int(match.group(1)) - 1   # convert to 0-indexed
            score      = int(match.group(2))
            if 0 <= chunk_idx < num_chunks and 1 <= score <= 10:
                scores[chunk_idx] = score

    return scores


def rerank_chunks(question: str, chunks: List[Dict]) -> List[Dict]:
    """
    Send chunks to Gemini for relevance scoring.
    Returns chunks sorted by Gemini score, filtered to top N.
    Falls back to similarity ordering if Gemini fails.
    """
    if not chunks:
        return chunks

    prompt = build_rerank_prompt(question, chunks)

    try:
        response   = model.generate_content(prompt)
        scores     = parse_rerank_scores(response.text, len(chunks))

        # Attach scores to chunks
        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = scores[i]

        # Sort by rerank score descending
        scored_chunks = sorted(chunks, key=lambda c: c["rerank_score"], reverse=True)

        # Keep chunks scoring above MIN_RERANK_SCORE
        top_chunks = [c for c in scored_chunks if c["rerank_score"] >= MIN_RERANK_SCORE]

        # Edge case: fewer than EXPLAIN_TOP_N chunks scored well
        # Lower threshold rather than returning too few results
        if len(top_chunks) < EXPLAIN_TOP_N:
            print(f"  [INFO] Only {len(top_chunks)} chunks scored ≥{MIN_RERANK_SCORE}. "
                  f"Lowering threshold to {LOWERED_THRESHOLD}")
            top_chunks = [c for c in scored_chunks if c["rerank_score"] >= LOWERED_THRESHOLD]

        # Cap at EXPLAIN_TOP_N
        return top_chunks[:EXPLAIN_TOP_N]

    except Exception as e:
        print(f"  [WARN] Re-ranking failed: {e}")
        print(f"  [FALLBACK] Using cosine similarity ordering")
        # Fallback: just return top N by similarity score
        return sorted(chunks, key=lambda c: c["similarity"], reverse=True)[:EXPLAIN_TOP_N]


# ── FIND_ALL path ───────────────────────────────────────────────

def filter_find_all(chunks: List[Dict]) -> List[Dict]:
    """
    For FIND_ALL intent: return every chunk above similarity threshold.
    No re-ranking — we want ALL occurrences, not just the best 3.
    """
    above_threshold = [c for c in chunks if c["similarity"] >= FIND_ALL_THRESHOLD]

    if not above_threshold:
        # No chunks above 0.75 — lower bar and return all
        print(f"  [INFO] No chunks above {FIND_ALL_THRESHOLD} threshold.")
        print(f"  [INFO] Returning all chunks sorted by similarity.")
        return sorted(chunks, key=lambda c: c["similarity"], reverse=True)

    return sorted(above_threshold, key=lambda c: c["similarity"], reverse=True)


# ── Main entry point ────────────────────────────────────────────

def rerank(question: str, chunks: List[Dict]) -> Dict:
    """
    Main Phase 5 entry point.

    Args:
        question: User's original question
        chunks:   Retrieved chunks from Phase 4

    Returns:
        Dict with final chunks + intent + metadata
    """
    print(f"\n=== Phase 5: Intent Detection + Re-ranking ===")
    print(f"Question: {question}")
    print(f"Input chunks: {len(chunks)}")

    # ── Step 1: Detect intent ────────────────────────────────────
    print("\n[1/2] Detecting intent...")
    intent = detect_intent(question)
    print(f"  ✓ Intent: {intent}")

    # ── Step 2: Fork based on intent ────────────────────────────
    print(f"\n[2/2] {'Re-ranking' if intent == 'EXPLAIN' else 'Filtering'} chunks...")

    if intent == "EXPLAIN":
        # Send to Gemini for scoring, keep top 3
        final_chunks = rerank_chunks(question, chunks)
        print(f"  ✓ Kept {len(final_chunks)} chunks after re-ranking")
        for c in final_chunks:
            score = c.get('rerank_score', 'N/A')
            print(f"    {c['file']}:{c['start_line']} "
                  f"(similarity: {c['similarity']}, rerank: {score})")

    else:  # FIND_ALL
        # Return everything above threshold
        final_chunks = filter_find_all(chunks)
        print(f"  ✓ {len(final_chunks)} chunks above threshold ({FIND_ALL_THRESHOLD})")
        for c in final_chunks:
            print(f"    {c['file']}:{c['start_line']} "
                  f"(similarity: {c['similarity']})")

    return {
        "question":     question,
        "intent":       intent,
        "final_chunks": final_chunks,
        "stats": {
            "input_chunks":  len(chunks),
            "output_chunks": len(final_chunks),
            "intent":        intent
        }
    }