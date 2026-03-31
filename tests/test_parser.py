import re

import pytest

from ingestion.chunker import chunk_contract
from ingestion.pdf_parser import parse_pdf


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_parsed(contract_id: str = "test_contract", n_pages: int = 2) -> dict:
    """Return a synthetic parsed dict that chunk_contract() can consume."""
    return {
        "contract_id": contract_id,
        "filename": f"{contract_id}.pdf",
        "pages": [
            # Each page has 600 chars so the splitter produces multiple chunks.
            {"page_number": i + 1, "text": f"Page {i + 1} content. " + ("X" * 580)}
            for i in range(n_pages)
        ],
    }


# ---------------------------------------------------------------------------
# Test 1 — parse_pdf raises FileNotFoundError for a missing file
# ---------------------------------------------------------------------------

def test_parse_pdf_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        parse_pdf("this_file_does_not_exist.pdf")


# ---------------------------------------------------------------------------
# Test 2 — chunk_contract returns chunks with correct structure
# ---------------------------------------------------------------------------

def test_chunk_contract_structure():
    result = chunk_contract(_make_parsed())

    assert "contract_id" in result
    assert "filename" in result
    assert "chunks" in result
    assert len(result["chunks"]) > 0, "Expected at least one chunk"

    for chunk in result["chunks"]:
        assert "chunk_id" in chunk, "chunk missing 'chunk_id'"
        assert "page_number" in chunk, "chunk missing 'page_number'"
        assert "text" in chunk, "chunk missing 'text'"
        assert isinstance(chunk["page_number"], int), "page_number must be int"
        assert len(chunk["text"]) > 0, "chunk text must not be empty"


# ---------------------------------------------------------------------------
# Test 3 — chunk_id format matches {contract_id}_chunk_{4 digits}
# ---------------------------------------------------------------------------

def test_chunk_id_format():
    contract_id = "my_contract"
    result = chunk_contract(_make_parsed(contract_id=contract_id))

    pattern = re.compile(rf"^{re.escape(contract_id)}_chunk_\d{{4}}$")
    for chunk in result["chunks"]:
        assert pattern.match(chunk["chunk_id"]), (
            f"chunk_id {chunk['chunk_id']!r} does not match "
            f"pattern '{contract_id}_chunk_NNNN'"
        )
