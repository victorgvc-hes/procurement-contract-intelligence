import logging
import os

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

MIN_PAGE_CHARS = 50


def parse_pdf(filepath: str) -> dict:
    """Parse a PDF file page by page using PyMuPDF.

    Args:
        filepath: Absolute or relative path to a PDF file.

    Returns:
        {
            "contract_id": str,   # filename without extension
            "filename":    str,   # basename of filepath
            "pages": [
                {"page_number": int, "text": str},  # 1-indexed, stripped
                ...
            ]
        }

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"PDF not found: {filepath}")

    filename = os.path.basename(filepath)
    contract_id = os.path.splitext(filename)[0]

    doc = fitz.open(filepath)
    pages: list[dict] = []

    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if len(text) < MIN_PAGE_CHARS:
            continue
        pages.append({"page_number": i + 1, "text": text})

    doc.close()

    if not pages:
        logger.warning("No extractable text pages found in '%s'", filename)

    return {
        "contract_id": contract_id,
        "filename": filename,
        "pages": pages,
    }
