import re
import time
from typing import List, Dict

FIND_ALL_THRESHOLD = 0.45
EXPLAIN_TOP_N      = 3
MIN_RERANK_SCORE   = 5
LOWERED_THRESHOLD  = 3


def detect_intent(question: str, provider: str, api_key: str, model: str) -> str:
    from backend.utils.llm import call_llm

    prompt = f"""Classify this developer question into exactly one category:

EXPLAIN  - The user wants to understand how something works or wants an explanation.
           Examples: "how does authentication work?", "what does verify_token do?"

FIND_ALL - The user wants to locate every place something appears or find all usages.
           Examples: "where is push_appctx used?", "find all places MAX_RETRIES appears"

Question: "{question}"

Rules:
- If ambiguous or asks both how AND where, answer FIND_ALL
- Reply with ONLY the single word: EXPLAIN or FIND_ALL"""

    try:
        intent = call_llm(prompt, provider, api_key, model).upper()
        if intent not in ("EXPLAIN", "FIND_ALL"):
            print(f"  [WARN] Unexpected intent: '{intent}' — defaulting to FIND_ALL")
            return "FIND_ALL"
        return intent
    except Exception as e:
        print(f"  [WARN] Intent detection failed: {e} — defaulting to FIND_ALL")
        return "FIND_ALL"


def build_rerank_prompt(question: str, chunks: List[Dict]) -> str:
    chunks_text = ""
    for i, chunk in enumerate(chunks):
        chunks_text += f"""
CHUNK {i+1}:
File: {chunk['file']} (lines {chunk['start_line']}-{chunk['end_line']})
Type: {chunk['chunk_type']}
Content:
{chunk['content'][:500]}
---"""

    return f"""You are a code search re-ranker. Score each chunk for relevance.

Question: "{question}"

{chunks_text}

Score each chunk from 1-10 where:
10 = directly answers the question
7  = highly relevant
5  = somewhat relevant
1  = not relevant

Reply in this EXACT format, one line per chunk:
CHUNK 1: <score>
CHUNK 2: <score>
(continue for all {len(chunks)} chunks)"""


def parse_rerank_scores(response_text: str, num_chunks: int) -> List[int]:
    scores = [5] * num_chunks
    for line in response_text.strip().split("\n"):
        match = re.search(r'CHUNK\s+(\d+):\s*(\d+)', line, re.IGNORECASE)
        if match:
            chunk_idx = int(match.group(1)) - 1
            score     = int(match.group(2))
            if 0 <= chunk_idx < num_chunks and 1 <= score <= 10:
                scores[chunk_idx] = score
    return scores


def rerank_chunks(question: str, chunks: List[Dict], provider: str, api_key: str, model: str) -> List[Dict]:
    from backend.utils.llm import call_llm

    if not chunks:
        return chunks

    prompt = build_rerank_prompt(question, chunks)

    try:
        response_text = call_llm(prompt, provider, api_key, model)
        scores        = parse_rerank_scores(response_text, len(chunks))

        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = scores[i]

        scored_chunks = sorted(chunks, key=lambda c: c["rerank_score"], reverse=True)
        top_chunks    = [c for c in scored_chunks if c["rerank_score"] >= MIN_RERANK_SCORE]

        if len(top_chunks) < EXPLAIN_TOP_N:
            print(f"  [INFO] Only {len(top_chunks)} chunks scored ≥{MIN_RERANK_SCORE}. "
                  f"Lowering threshold to {LOWERED_THRESHOLD}")
            top_chunks = [c for c in scored_chunks if c["rerank_score"] >= LOWERED_THRESHOLD]

        return top_chunks[:EXPLAIN_TOP_N]

    except Exception as e:
        print(f"  [WARN] Re-ranking failed: {e}")
        print(f"  [FALLBACK] Using cosine similarity ordering")
        return sorted(chunks, key=lambda c: c["similarity"], reverse=True)[:EXPLAIN_TOP_N]


def filter_find_all(chunks: List[Dict]) -> List[Dict]:
    above_threshold = [c for c in chunks if c["similarity"] >= FIND_ALL_THRESHOLD]

    if not above_threshold:
        print(f"  [INFO] No chunks above {FIND_ALL_THRESHOLD} threshold.")
        print(f"  [INFO] Returning all chunks sorted by similarity.")
        return sorted(chunks, key=lambda c: c["similarity"], reverse=True)

    return sorted(above_threshold, key=lambda c: c["similarity"], reverse=True)


def rerank(
    question: str,
    chunks:   List[Dict],
    provider: str,
    api_key:  str,
    model:    str = None
) -> Dict:
    """
    Main Phase 5 entry point.

    Args:
        question: User's original question
        chunks:   Retrieved chunks from Phase 4
        provider: LLM provider (openrouter / groq / openai / anthropic)
        api_key:  User's decrypted LLM API key
        model:    LLM model name
    """
    print(f"\n=== Phase 5: Intent Detection + Re-ranking ===")
    print(f"Question: {question}")
    print(f"Input chunks: {len(chunks)}")

    print("\n[1/2] Detecting intent...")
    intent = detect_intent(question, provider, api_key, model)
    print(f"  ✓ Intent: {intent}")

    print(f"\n[2/2] {'Re-ranking' if intent == 'EXPLAIN' else 'Filtering'} chunks...")

    if intent == "EXPLAIN":
        final_chunks = rerank_chunks(question, chunks, provider, api_key, model)
        print(f"  ✓ Kept {len(final_chunks)} chunks after re-ranking")
        for c in final_chunks:
            score = c.get('rerank_score', 'N/A')
            print(f"    {c['file']}:{c['start_line']} "
                  f"(similarity: {c['similarity']}, rerank: {score})")
    else:
        final_chunks = filter_find_all(chunks)
        print(f"  ✓ {len(final_chunks)} chunks returned")
        for c in final_chunks:
            print(f"    {c['file']}:{c['start_line']} (similarity: {c['similarity']})")

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