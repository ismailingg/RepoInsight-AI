import os
import hashlib
from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript

# ── Language setup ──────────────────────────────────────────────
LANGUAGE_MAP = {
    "py": Language(tspython.language()),
    "js": Language(tsjavascript.language()),
}

MAX_FUNCTION_LINES = 200
OVERLAP_LINES      = 5
FALLBACK_WINDOW    = 50
MAX_TOTAL_CHUNKS   = 2000   # repo-level cap

# File patterns
TEST_PATTERNS     = ["test_", "_test.py", "spec_", ".spec.js", "conftest.py"]
EXAMPLE_PATTERNS  = ["examples/", "tutorial/", "docs/"]
PRIORITY_FILES    = ["app.py", "main.py", "index.js", "__init__.py",
                     "views.py", "models.py", "routes.py", "middleware.py"]


# ── File classification helpers ─────────────────────────────────

def is_test_file(relative_path: str) -> bool:
    """Check if file is a test file."""
    name = os.path.basename(relative_path).lower()
    return any(p in name for p in TEST_PATTERNS)


def is_example_file(relative_path: str) -> bool:
    """Check if file is in examples/tutorials."""
    path_lower = relative_path.lower().replace("\\", "/")
    return any(p in path_lower for p in EXAMPLE_PATTERNS)


def file_priority(relative_path: str, skip_tests: bool = True) -> int:
    """
    Return priority score for processing order:
    2 = core files (always process first)
    1 = normal files
    0 = tests/examples (process last, skip first if cap hit)
    """
    name = os.path.basename(relative_path).lower()
    
    # Core files always highest priority
    if any(p in name for p in PRIORITY_FILES):
        return 2
    
    # Tests get lowest priority only if skip_tests=True
    if skip_tests and is_test_file(relative_path):
        return 0
    
    return 1  # everything else


# ── Chunking helpers ────────────────────────────────────────────

def _make_id(relative_path: str, start_line: int) -> str:
    """Stable unique ID for a chunk."""
    raw = f"{relative_path}:{start_line}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


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
        i += window - OVERLAP_LINES
    return chunks


def _line_based_chunks(lines: list[str], relative_path: str,
                        language: str) -> list[dict]:
    """50-line windows with 5-line overlap for unsupported languages."""
    chunks = []
    i = 0
    while i < len(lines):
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


def _treesitter_chunks(source: str, relative_path: str,
                        language: str) -> list[dict]:
    """Parse file into function/class chunks using tree-sitter AST."""
    parser = Parser(LANGUAGE_MAP[language])
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)
    root = tree.root_node

    TARGET_TYPES = {"function_definition", "class_definition",
                    "function_declaration", "class_declaration",
                    "method_definition", "arrow_function"}

    chunks = []
    all_lines = source.splitlines()

    def visit(node):
        if node.type in TARGET_TYPES:
            start = node.start_point[0]
            end   = node.end_point[0]
            chunk_type = "class" if "class" in node.type else "function"
            node_lines = all_lines[start:end + 1]

            if len(node_lines) > MAX_FUNCTION_LINES:
                chunks.extend(
                    _split_long_function(node_lines, start + 1, relative_path, language)
                )
            else:
                chunks.append({
                    "chunk_id":      _make_id(relative_path, start + 1),
                    "content":       "\n".join(node_lines),
                    "relative_path": relative_path,
                    "start_line":    start + 1,
                    "end_line":      end + 1,
                    "language":      language,
                    "chunk_type":    chunk_type,
                })
            return  # don't recurse into children

        for child in node.children:
            visit(child)

    visit(root)

    # If no functions/classes found, treat whole file as one chunk
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


def _add_overlap(chunks: list[dict]) -> list[dict]:
    """Add 5-line overlap between adjacent chunks."""
    for i in range(len(chunks) - 1):
        next_lines = chunks[i + 1]["content"].splitlines()
        overlap = "\n".join(next_lines[:OVERLAP_LINES])
        chunks[i]["content"] += f"\n# --- overlap ---\n{overlap}"
    return chunks


# ── Main chunking functions ─────────────────────────────────────

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

    if len(all_lines) > 1000:
        print(f"[INFO] Large file ({len(all_lines)} lines): {rel_path}")

    # Route to correct chunker
    if language in LANGUAGE_MAP:
        chunks = _treesitter_chunks(source, rel_path, language)
    else:
        chunks = _line_based_chunks(all_lines, rel_path, language)

    # Add overlap between adjacent chunks
    chunks = _add_overlap(chunks)

    return chunks


def chunk_all_files(files: list[dict], 
                    skip_tests: bool = True,
                    skip_examples: bool = True) -> list[dict]:
    """
    Run chunk_file() on every file from Phase 1.
    
    Args:
        files: List from Phase 1 (walk_repo output)
        skip_tests: If True, process test files last (lower priority)
        skip_examples: If True, filter out example/tutorial files entirely
    
    Returns:
        Flat list of all chunks across the entire repo.
    """
    all_chunks = []

    # Filter out examples if requested
    if skip_examples:
        before = len(files)
        files = [f for f in files if not is_example_file(f["relative_path"])]
        removed = before - len(files)
        if removed > 0:
            print(f"[INFO] Filtered out {removed} example/tutorial files\n")

    # Sort by priority: core files first, tests last
    sorted_files = sorted(
        files, 
        key=lambda f: file_priority(f["relative_path"], skip_tests=skip_tests), 
        reverse=True
    )

    for file_info in sorted_files:
        # Stop if we hit the repo-level cap
        if len(all_chunks) >= MAX_TOTAL_CHUNKS:
            skipped = len(sorted_files) - sorted_files.index(file_info)
            print(f"\n[WARN] Repo chunk cap ({MAX_TOTAL_CHUNKS}) reached.")
            print(f"       Skipped {skipped} lower-priority files (tests/examples).")
            break

        chunks = chunk_file(file_info)
        all_chunks.extend(chunks)
        
        # Mark test files in output
        marker = " [test]" if is_test_file(file_info["relative_path"]) else ""
        print(f"  ✓ {file_info['relative_path']}{marker} → {len(chunks)} chunks")

    print(f"\n✓ Total chunks: {len(all_chunks)}")
    return all_chunks