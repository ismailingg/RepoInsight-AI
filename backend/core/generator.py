import re
import time
from typing import List, Dict, Optional

OUT_OF_SCOPE_THRESHOLD = 0.2
WIDE_ANSWER_FILE_CAP   = 5
MAX_CONTEXT_CHARS      = 40000


def expand_query(question: str, provider: str, api_key: str, model: str) -> List[str]:
    from backend.utils.llm import call_llm

    prompt = f"""You are helping search a codebase. Rewrite this developer question
into 3 specific sub-questions that together cover all aspects of the answer.

Original question: "{question}"

Rules:
- Each sub-question must be specific and searchable
- Cover different aspects (definition, usage, configuration)
- Keep each sub-question under 15 words
- Reply with ONLY 3 lines, one sub-question per line, no numbering"""

    try:
        response_text = call_llm(prompt, provider, api_key, model)
        sub_questions = [
            line.strip()
            for line in response_text.split("\n")
            if line.strip()
        ][:3]

        while len(sub_questions) < 3:
            sub_questions.append(question)

        return sub_questions

    except Exception as e:
        print(f"  [WARN] Query expansion failed: {e} — using original question")
        return [question, question, question]


def is_out_of_scope(chunks: List[Dict]) -> bool:
    if not chunks:
        return True
    max_similarity = max(c["similarity"] for c in chunks)
    return max_similarity < OUT_OF_SCOPE_THRESHOLD


def validate_citations(answer: str, valid_files: List[str]) -> str:
    file_pattern  = re.compile(r'\b[\w/\\]+\.(?:py|js|ts|java|go|rb|php|cs|cpp|c|swift)\b')
    mentioned     = file_pattern.findall(answer)
    hallucinated  = []

    for f in mentioned:
        normalized       = f.replace("\\", "/")
        valid_normalized = [v.replace("\\", "/") for v in valid_files]
        if normalized not in valid_normalized:
            hallucinated.append(f)

    if hallucinated:
        warning = (f"\n\n⚠️ Note: The following files were cited but could not be "
                   f"verified in the indexed codebase: {', '.join(hallucinated)}")
        answer += warning
        print(f"  [WARN] Hallucinated citations: {hallucinated}")

    return answer


def calculate_confidence(chunks: List[Dict]) -> float:
    if not chunks:
        return 0.0
    avg_similarity = sum(c["similarity"] for c in chunks) / len(chunks)
    both_bonus     = min(0.1, sum(1 for c in chunks if c.get("source") == "both") * 0.03)
    coverage_bonus = min(0.05, len(chunks) * 0.01)
    return round(min(1.0, avg_similarity + both_bonus + coverage_bonus), 3)


def summarize_files(question: str, chunks: List[Dict], provider: str, api_key: str, model: str) -> str:
    from backend.utils.llm import call_llm

    files = {}
    for chunk in chunks:
        f = chunk["file"]
        if f not in files:
            files[f] = []
        files[f].append(chunk)

    file_summaries = []
    for filepath, file_chunks in files.items():
        combined = "\n\n".join(c["content"][:300] for c in file_chunks)
        file_summaries.append(f"File: {filepath}\n{combined}")

    summaries_text = "\n\n---\n\n".join(file_summaries)

    prompt = f"""Question: "{question}"

For each file below, write ONE sentence describing how it relates to the question.

{summaries_text[:8000]}

Reply with one line per file: <filename>: <one sentence>"""

    try:
        return call_llm(prompt, provider, api_key, model)
    except Exception as e:
        print(f"  [WARN] File summarization failed: {e}")
        return "\n".join(f"{f}: relevant file" for f in files.keys())


def build_answer_prompt(question: str, chunks: List[Dict], file_summaries: str = None) -> str:
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

    summary_section = ""
    if file_summaries:
        summary_section = f"\nFILE ROLE SUMMARY:\n{file_summaries}\n"

    return f"""You are a codebase expert answering questions about source code.
Answer based ONLY on the provided code context. Do not invent or assume.

Question: "{question}"

{summary_section}
CODE CONTEXT:
{context}

Instructions:
- Answer clearly and specifically
- Cite every file and line number you reference like this: [filename:line]
- If the answer spans multiple files, explain each file's role
- If something is unclear from the context, say so
- End with a brief summary sentence

Answer:"""


def generate_answer(
    question:    str,
    chunks:      List[Dict],
    valid_files: List[str],
    provider:    str,
    api_key:     str,
    model:       str
) -> str:
    from backend.utils.llm import call_llm

    prompt = build_answer_prompt(question, chunks)

    try:
        answer_text = call_llm(prompt, provider, api_key, model, max_tokens=2048)
        answer_text = validate_citations(answer_text, valid_files)
        return answer_text
    except Exception as e:
        print(f"  [ERROR] Answer generation failed: {e}")
        return f"Error generating answer: {e}"


def generate(
    question:     str,
    final_chunks: List[Dict],
    repo_url:     str,
    all_chunks:   List[Dict],
    valid_files:  List[str],
    provider:     str,
    api_key:      str,
    model:        str,
    retrieve_fn,
    rerank_fn
) -> Dict:
    """
    Main Phase 6 entry point.

    Args:
        question:     User question
        final_chunks: Chunks from Phase 5
        repo_url:     GitHub URL
        all_chunks:   All cached chunks (for grep in sub-questions)
        valid_files:  All file paths (for citation validation)
        provider:     LLM provider
        api_key:      User's decrypted LLM key
        model:        LLM model name
        retrieve_fn:  Phase 4 function
        rerank_fn:    Phase 5 function
    """
    print(f"\n=== Phase 6: Answer Generation ===")
    print(f"Question: {question}")
    print(f"Input chunks: {len(final_chunks)}")

    # Step 1: Out-of-scope check
    print("\n[1/5] Checking scope...")
    if is_out_of_scope(final_chunks):
        print(f"  [OUT OF SCOPE] Max similarity below {OUT_OF_SCOPE_THRESHOLD}")
        return {
            "answer":     "This question doesn't appear to be about this codebase. "
                          "Try asking something more specific to the repository.",
            "sources":    [],
            "confidence": 0.0,
            "intent":     "out_of_scope"
        }
    print(f"  ✓ In scope (max similarity: {max(c['similarity'] for c in final_chunks):.3f})")

    # Step 2: Query expansion
    print("\n[2/5] Expanding query...")
    sub_questions = expand_query(question, provider, api_key, model)
    print(f"  ✓ Sub-questions:")
    for q in sub_questions:
        print(f"    • {q}")

    expanded_chunks = list(final_chunks)
    seen_ids = {c["chunk_id"] for c in final_chunks}

    for sub_q in sub_questions:
        try:
            sub_retrieval = retrieve_fn(sub_q, repo_url, all_chunks)
            sub_reranked  = rerank_fn(sub_q, sub_retrieval["chunks"])
            for chunk in sub_reranked["final_chunks"]:
                if chunk["chunk_id"] not in seen_ids:
                    expanded_chunks.append(chunk)
                    seen_ids.add(chunk["chunk_id"])
            time.sleep(1)
        except Exception as e:
            print(f"  [WARN] Sub-question retrieval failed: {e}")

    print(f"  ✓ Expanded from {len(final_chunks)} → {len(expanded_chunks)} chunks")

    # Step 3: Wide answer check
    print("\n[3/5] Checking answer breadth...")
    unique_files   = list(set(c["file"] for c in expanded_chunks))
    file_summaries = None

    if len(unique_files) >= WIDE_ANSWER_FILE_CAP:
        print(f"  [WIDE] Answer spans {len(unique_files)} files — two-pass summarization")
        file_summaries = summarize_files(question, expanded_chunks, provider, api_key, model)
        print(f"  ✓ File summaries generated")
    else:
        print(f"  ✓ Answer spans {len(unique_files)} files — single pass")

    # Step 4: Generate answer
    print("\n[4/5] Generating answer...")
    answer_text = generate_answer(question, expanded_chunks, valid_files, provider, api_key, model)
    print(f"  ✓ Answer generated ({len(answer_text)} chars)")

    # Step 5: Build response
    print("\n[5/5] Building structured response...")
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