import re
import json
import time
from typing import List, Dict, Optional
# import google.generativeai as genai
# from backend.config import GOOGLE_API_KEY, GEMINI_MODEL

# # Initialize Gemini
# genai.configure(api_key=GOOGLE_API_KEY)
# model = genai.GenerativeModel(GEMINI_MODEL)
from backend.utils.llm import call_llm

# Constants
OUT_OF_SCOPE_THRESHOLD = 0.4   # below this = question not about this codebase
WIDE_ANSWER_FILE_CAP   = 5     # above this many files = use two-pass summarization
MAX_CONTEXT_CHARS      = 12000 # max total chars to send to Gemini in one call


# ── Query Expansion ─────────────────────────────────────────────

def expand_query(question: str) -> List[str]:
    """
    Ask Gemini to rewrite the question into 3 specific sub-questions.
    This catches answers spread across multiple aspects of the codebase.
    
    Example:
      Input:  "how does flask handle errors?"
      Output: ["how does flask catch exceptions in routes?",
               "where is error handling middleware defined?",
               "what is the default error response format?"]
    """
    prompt = f"""You are helping search a codebase. Rewrite this developer question 
into 3 specific sub-questions that together cover all aspects of the answer.
Each sub-question should focus on a different angle.

Original question: "{question}"

Rules:
- Each sub-question must be specific and searchable
- Cover different aspects (definition, usage, configuration)
- Keep each sub-question under 15 words
- Reply with ONLY 3 lines, one sub-question per line, no numbering, no bullets"""

    try:
        response = call_llm(prompt)
        sub_questions = [
            line.strip()
            for line in response_text.strip().split("\n")
            if line.strip()
        ][:3]   # take max 3

        # Fallback if Gemini returns fewer than 3
        while len(sub_questions) < 3:
            sub_questions.append(question)

        return sub_questions

    except Exception as e:
        print(f"  [WARN] Query expansion failed: {e} — using original question")
        return [question, question, question]


# ── Out-of-scope check ──────────────────────────────────────────

def is_out_of_scope(chunks: List[Dict]) -> bool:
    """
    Check if the question is out of scope for this codebase.
    If no chunks score above OUT_OF_SCOPE_THRESHOLD, the question
    is probably about an external library or unrelated topic.
    """
    if not chunks:
        return True

    max_similarity = max(c["similarity"] for c in chunks)
    return max_similarity < OUT_OF_SCOPE_THRESHOLD


# ── Citation validation ─────────────────────────────────────────

def validate_citations(answer: str, valid_files: List[str]) -> str:
    """
    Check answer text for hallucinated file citations.
    If Gemini mentions a file that doesn't exist in valid_files,
    replace it with a warning note.
    """
    # Find all file-like patterns in the answer
    # Matches things like: auth/login.py, src/flask/app.py
    file_pattern = re.compile(r'\b[\w/\\]+\.(?:py|js|ts|java|go|rb|php)\b')
    mentioned_files = file_pattern.findall(answer)

    hallucinated = []
    for mentioned in mentioned_files:
        # Normalize path separators for comparison
        normalized = mentioned.replace("\\", "/")
        valid_normalized = [f.replace("\\", "/") for f in valid_files]

        if normalized not in valid_normalized:
            hallucinated.append(mentioned)

    if hallucinated:
        warning = (f"\n\n⚠️ Note: The following files were cited but could not be "
                   f"verified in the indexed codebase: {', '.join(hallucinated)}")
        answer += warning
        print(f"  [WARN] Hallucinated citations detected: {hallucinated}")

    return answer


# ── Confidence score ────────────────────────────────────────────

def calculate_confidence(chunks: List[Dict]) -> float:
    """
    Calculate a confidence score for the answer based on:
    - Average similarity of top chunks
    - Whether chunks were found by both semantic + grep
    - Number of chunks available
    """
    if not chunks:
        return 0.0

    # Base: average similarity of chunks used
    avg_similarity = sum(c["similarity"] for c in chunks) / len(chunks)

    # Bonus: chunks found by both searches
    both_count = sum(1 for c in chunks if c.get("source") == "both")
    both_bonus = min(0.1, both_count * 0.03)

    # Bonus: more chunks = more evidence
    coverage_bonus = min(0.05, len(chunks) * 0.01)

    confidence = avg_similarity + both_bonus + coverage_bonus
    return round(min(1.0, confidence), 3)


# ── Two-pass summarization (wide answers) ──────────────────────

def summarize_files(question: str, chunks: List[Dict]) -> str:
    """
    For wide answers (5+ files): summarize each file's role first,
    then synthesize in a second call.
    Prevents stuffing too much context into one giant prompt.
    """
    # Group chunks by file
    files = {}
    for chunk in chunks:
        f = chunk["file"]
        if f not in files:
            files[f] = []
        files[f].append(chunk)

    # First pass: summarize each file's contribution
    file_summaries = []
    for filepath, file_chunks in files.items():
        combined_content = "\n\n".join(
            c["content"][:300] for c in file_chunks
        )
        file_summaries.append(
            f"File: {filepath}\n"
            f"Relevant code:\n{combined_content}"
        )

    summaries_text = "\n\n---\n\n".join(file_summaries)

    summary_prompt = f"""Question: "{question}"

The following files are relevant. For each file, write ONE sentence 
describing how it relates to the question.

{summaries_text[:8000]}

Reply with one line per file in format:
<filename>: <one sentence description>"""

    try:
       return call_llm(summary_prompt)
    except Exception as e:
        print(f"  [WARN] File summarization failed: {e}")
        # Fallback: just concatenate file names and first chunk content
        return "\n".join(
            f"{f}: {chunks[0]['content'][:200]}"
            for f, chunks in files.items()
        )


# ── Main answer generation ──────────────────────────────────────

def build_answer_prompt(question: str, chunks: List[Dict],
                         file_summaries: str = None) -> str:
    """Build the final answer generation prompt."""

    # Format chunks as context
    context_parts = []
    total_chars   = 0

    for chunk in chunks:
        chunk_text = (
            f"File: {chunk['file']} "
            f"(lines {chunk['start_line']}-{chunk['end_line']})\n"
            f"{chunk['content']}"
        )

        if total_chars + len(chunk_text) > MAX_CONTEXT_CHARS:
            print(f"  [INFO] Context limit reached — using {len(context_parts)} chunks")
            break

        context_parts.append(chunk_text)
        total_chars += len(chunk_text)

    context = "\n\n---\n\n".join(context_parts)

    # Add file summaries if wide answer
    summary_section = ""
    if file_summaries:
        summary_section = f"""
FILE ROLE SUMMARY:
{file_summaries}

"""

    return f"""You are a codebase expert answering questions about source code.
Answer based ONLY on the provided code context. Do not invent or assume.

Question: "{question}"

{summary_section}CODE CONTEXT:
{context}

Instructions:
- Answer clearly and specifically
- Cite every file and line number you reference like this: [filename:line]
- If the answer spans multiple files, explain each file's role
- If something is unclear from the context, say so explicitly
- End with a brief summary sentence

Answer:"""


def generate_answer(question: str, chunks: List[Dict],
                    valid_files: List[str]) -> Dict:
    """
    Generate a cited answer from the final chunks.
    Returns structured JSON with answer, sources, confidence.
    """
    prompt = build_answer_prompt(question, chunks)

    try:
        answer_text = call_llm(prompt)

        # Validate citations
        answer_text = validate_citations(answer_text, valid_files)

        return answer_text

    except Exception as e:
        print(f"  [ERROR] Answer generation failed: {e}")
        return f"Error generating answer: {e}"


# ── Main Phase 6 entry point ────────────────────────────────────

def generate(
    question:     str,
    final_chunks: List[Dict],
    repo_url:     str,
    all_chunks:   List[Dict],
    valid_files:  List[str],
    retrieve_fn,
    rerank_fn
) -> Dict:
    """
    Main Phase 6 entry point.

    Args:
        question:     Original user question
        final_chunks: Chunks from Phase 5
        repo_url:     GitHub URL (for re-retrieval)
        all_chunks:   All cached chunks (for grep search)
        valid_files:  List of all file paths (for citation validation)
        retrieve_fn:  Phase 4 retrieve() function
        rerank_fn:    Phase 5 rerank() function

    Returns:
        Structured dict: answer, sources, confidence
    """
    print(f"\n=== Phase 6: Answer Generation ===")
    print(f"Question: {question}")
    print(f"Input chunks: {len(final_chunks)}")

    # ── Step 1: Out-of-scope check ───────────────────────────────
    print("\n[1/5] Checking if question is in scope...")
    if is_out_of_scope(final_chunks):
        print(f"  [OUT OF SCOPE] Max similarity below {OUT_OF_SCOPE_THRESHOLD}")
        return {
            "answer":     "This question doesn't appear to be about this codebase. "
                          "Try asking something more specific to the repository.",
            "sources":    [],
            "confidence": 0.0,
            "intent":     "out_of_scope"
        }
    print(f"  ✓ In scope (max similarity: "
          f"{max(c['similarity'] for c in final_chunks):.3f})")

    # ── Step 2: Query expansion ──────────────────────────────────
    print("\n[2/5] Expanding query...")
    sub_questions = expand_query(question)
    print(f"  ✓ Sub-questions:")
    for q in sub_questions:
        print(f"    • {q}")

    # Re-retrieve for each sub-question and merge
    expanded_chunks = list(final_chunks)   # start with Phase 5 chunks
    seen_ids = {c["chunk_id"] for c in final_chunks}

    for sub_q in sub_questions:
        try:
            sub_retrieval = retrieve_fn(sub_q, repo_url, all_chunks)
            sub_reranked  = rerank_fn(sub_q, sub_retrieval["chunks"])

            # Add new chunks not already in our set
            for chunk in sub_reranked["final_chunks"]:
                if chunk["chunk_id"] not in seen_ids:
                    expanded_chunks.append(chunk)
                    seen_ids.add(chunk["chunk_id"])

            time.sleep(1)   # small delay between Gemini calls

        except Exception as e:
            print(f"  [WARN] Sub-question retrieval failed: {e}")

    print(f"  ✓ Expanded from {len(final_chunks)} → {len(expanded_chunks)} chunks")

    # ── Step 3: Wide answer check ────────────────────────────────
    print("\n[3/5] Checking answer breadth...")
    unique_files   = list(set(c["file"] for c in expanded_chunks))
    file_summaries = None

    if len(unique_files) >= WIDE_ANSWER_FILE_CAP:
        print(f"  [WIDE] Answer spans {len(unique_files)} files — "
              f"running two-pass summarization")
        file_summaries = summarize_files(question, expanded_chunks)
        print(f"  ✓ File summaries generated")
    else:
        print(f"  ✓ Answer spans {len(unique_files)} files — single pass")

    # ── Step 4: Generate answer ──────────────────────────────────
    print("\n[4/5] Generating answer...")
    answer_text = generate_answer(question, expanded_chunks, valid_files)
    print(f"  ✓ Answer generated ({len(answer_text)} chars)")

    # ── Step 5: Build structured response ───────────────────────
    print("\n[5/5] Building structured response...")

    # Extract sources from chunks used
    sources = [
        {
            "file":    chunk["file"],
            "line":    chunk["start_line"],
            "snippet": chunk["content"][:100]
        }
        for chunk in expanded_chunks
    ]

    confidence = calculate_confidence(expanded_chunks)
    print(f"  ✓ Confidence: {confidence}")

    return {
        "answer":     answer_text,
        "sources":    sources,
        "confidence": confidence,
        "intent":     "answered"
    }