import os
import hashlib
from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript

# ── Language setup ──────────────────────────────────────────────
# Load grammars for supported languages
LANGUAGE_MAP = {
    "py":  Language(tspython.language()),
    "js":  Language(tsjavascript.language()),
}

# Chunk limits from build plan
MAX_CHUNKS_PER_FILE = 20
MAX_FUNCTION_LINES  = 200
OVERLAP_LINES       = 5
FALLBACK_WINDOW     = 50   # for unsupported languages


# ── Helpers ─────────────────────────────────────────────────────

def _make_id(relative_path: str, start_line: int) -> str:
    """Stable unique ID for a chunk."""
    raw = f"{relative_path}:{start_line}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _get_node_text(source_bytes: bytes, node) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _split_long_function(lines: list[str], start_line: int,
                          relative_path: str, language: str) -> list[dict]:
    """Sub-chunk a function longer than MAX_FUNCTION_LINES."""
    chunks = []
    window = MAX_FUNCTION_LINES
    i = 0
    while i < len(lines):
        chunk_lines = lines[i: i + window]
        actual_start = start_line + i
        chunks.append({
            "chunk_id":      _make_id(relative_path, actual_start),
            "content":       "\n".join(chunk_lines),
            "relative_path": relative_path,
            "start_line":    actual_start,
            "end_line":      actual_start + len(chunk_lines) - 1,
            "language":      language,
            "chunk_type":    "function-part",
        })
        i += window - OVERLAP_LINES   # overlap between sub-chunks
    return chunks


# ── Fallback: line-based chunking (unsupported languages) ────────

def _line_based_chunks(lines: list[str], relative_path: str,
                        language: str) -> list[dict]:
    """50-line windows with 5-line overlap for bash/SQL/YAML/etc."""
    chunks = []
    i = 0
    while i < len(lines) and len(chunks) < MAX_CHUNKS_PER_FILE:
        chunk_lines = lines[i: i + FALLBACK_WINDOW]
        chunks.append({
            "chunk_id":      _make_id(relative_path, i + 1),
            "content":       "\n".join(chunk_lines),
            "relative_path": relative_path,
            "start_line":    i + 1,
            "end_line":      i + len(chunk_lines),
            "language":      language,
            "chunk_type":    "module-level",
        })
        i += FALLBACK_WINDOW - OVERLAP_LINES
    return chunks


# ── Tree-sitter chunking (Python / JS) ──────────────────────────

def _treesitter_chunks(source: str, relative_path: str,
                        language: str) -> list[dict]:
    """Parse file into function/class chunks using tree-sitter AST."""
    parser = Parser(LANGUAGE_MAP[language])
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)
    root = tree.root_node

    # Node types that represent logical units
    TARGET_TYPES = {"function_definition", "class_definition",   # Python
                    "function_declaration", "class_declaration",  # JS
                    "method_definition", "arrow_function"}        # JS

    chunks = []
    all_lines = source.splitlines()

    def visit(node):
        if len(chunks) >= MAX_CHUNKS_PER_FILE:
            return

        if node.type in TARGET_TYPES:
            start = node.start_point[0]   # 0-indexed line
            end   = node.end_point[0]

            # Determine chunk type
            chunk_type = "function" if "function" in node.type or "method" in node.type or "arrow" in node.type else "class"

            node_lines = all_lines[start:end + 1]

            # Edge case: giant function → sub-chunk it
            if len(node_lines) > MAX_FUNCTION_LINES:
                chunks.extend(
                    _split_long_function(node_lines, start + 1, relative_path, language)
                )
            else:
                chunks.append({
                    "chunk_id":      _make_id(relative_path, start + 1),
                    "content":       "\n".join(node_lines),
                    "relative_path": relative_path,
                    "start_line":    start + 1,   # convert to 1-indexed
                    "end_line":      end + 1,
                    "language":      language,
                    "chunk_type":    chunk_type,
                })

            # Don't recurse into children — keep chunks at top level
            return

        for child in node.children:
            visit(child)

    visit(root)

    # If tree-sitter found nothing (e.g. a file with only imports),
    # treat the whole file as one module-level chunk
    if not chunks:
        chunks.append({
            "chunk_id":      _make_id(relative_path, 1),
            "content":       source,
            "relative_path": relative_path,
            "start_line":    1,
            "end_line":      len(all_lines),
            "language":      language,
            "chunk_type":    "module-level",
        })

    return chunks


# ── Add overlap between adjacent chunks ─────────────────────────

def _add_overlap(chunks: list[dict], all_lines: list[str]) -> list[dict]:
    """
    Append the first OVERLAP_LINES of chunk[N+1] to the end of chunk[N].
    This prevents a function call from being separated from its definition.
    """
    for i in range(len(chunks) - 1):
        next_content_lines = chunks[i + 1]["content"].splitlines()
        overlap = "\n".join(next_content_lines[:OVERLAP_LINES])
        chunks[i]["content"] += f"\n# --- overlap ---\n{overlap}"
    return chunks


# ── Main entry point ─────────────────────────────────────────────

def chunk_file(file_info: dict) -> list[dict]:
    """
    Takes one file dict from Phase 1 and returns a list of chunks.
    file_info = { "path", "relative_path", "language", "last_modified" }
    """
    path     = file_info["path"]
    rel_path = file_info["relative_path"]
    language = file_info["language"]

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as e:
        print(f"[WARN] Could not read {rel_path}: {e}")
        return []

    all_lines = source.splitlines()

    # Edge case: file over 1000 lines warning
    if len(all_lines) > 1000:
        print(f"[WARN] Large file ({len(all_lines)} lines): {rel_path} — capping at {MAX_CHUNKS_PER_FILE} chunks")

    # Route to correct chunker
    if language in LANGUAGE_MAP:
        chunks = _treesitter_chunks(source, rel_path, language)
    else:
        chunks = _line_based_chunks(all_lines, rel_path, language)

    # Add overlap between adjacent chunks
    chunks = _add_overlap(chunks, all_lines)

    return chunks


def chunk_all_files(files: list[dict]) -> list[dict]:
    """
    Run chunk_file() on every file from Phase 1.
    Returns flat list of all chunks across the entire repo.
    """
    all_chunks = []
    for file_info in files:
        chunks = chunk_file(file_info)
        all_chunks.extend(chunks)
        print(f"  ✓ {file_info['relative_path']} → {len(chunks)} chunks")

    print(f"\n✓ Total chunks: {len(all_chunks)}")
    return all_chunks