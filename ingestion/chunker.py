import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

_PAGE_MARKER_RE = re.compile(r'\[PAGE (\d+)\]')


def chunk_contract(parsed: dict) -> dict:
    """Split a parsed contract into overlapping text chunks.

    Args:
        parsed: Output of parse_pdf() — must contain 'contract_id',
                'filename', and 'pages'.

    Returns:
        {
            "contract_id": str,
            "filename":    str,
            "chunks": [
                {
                    "chunk_id":    str,  # "{contract_id}_chunk_{i:04d}"
                    "page_number": int,  # inferred from nearest [PAGE n] marker
                    "text":        str,
                },
                ...
            ]
        }
    """
    contract_id = parsed["contract_id"]
    filename = parsed["filename"]
    pages: list[dict] = parsed["pages"]

    # Build full text with explicit page boundary markers so page attribution
    # survives the split.
    parts: list[str] = []
    for page in pages:
        parts.append(f"[PAGE {page['page_number']}]\n{page['text']}")
    full_text = "\n\n".join(parts)

    # Index of (char_position, page_number) for every marker in full_text.
    page_positions: list[tuple[int, int]] = [
        (m.start(), int(m.group(1)))
        for m in _PAGE_MARKER_RE.finditer(full_text)
    ]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    raw_chunks: list[str] = splitter.split_text(full_text)

    chunks: list[dict] = []
    for i, chunk_text in enumerate(raw_chunks):
        chunks.append({
            "chunk_id": f"{contract_id}_chunk_{i:04d}",
            "page_number": _infer_page(chunk_text, full_text, page_positions),
            "text": chunk_text,
        })

    return {
        "contract_id": contract_id,
        "filename": filename,
        "chunks": chunks,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _infer_page(
    chunk_text: str,
    full_text: str,
    page_positions: list[tuple[int, int]],
) -> int:
    """Return the page number the chunk most likely belongs to.

    Strategy:
    1. If the chunk itself contains a [PAGE n] marker, use the *last* one
       (a chunk can span a page boundary; the last marker is the dominant page).
    2. Otherwise, locate the chunk inside full_text by its first 80 characters
       and walk the page_positions index to find the enclosing page.
    """
    markers = _PAGE_MARKER_RE.findall(chunk_text)
    if markers:
        return int(markers[-1])

    # Fall back to positional lookup
    if not page_positions:
        return 1

    search_key = chunk_text[:80]
    pos = full_text.find(search_key)
    if pos == -1:
        return page_positions[0][1]

    # Last marker whose position is <= chunk start
    page_num = page_positions[0][1]
    for char_pos, p_num in page_positions:
        if char_pos <= pos:
            page_num = p_num
        else:
            break
    return page_num
