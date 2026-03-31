import json
import logging
import os

from ingestion.chunker import chunk_contract
from ingestion.pdf_parser import parse_pdf

logger = logging.getLogger(__name__)


def run_pipeline(pdf_path: str, output_dir: str) -> str:
    """Parse a PDF contract and save overlapping chunks as JSON.

    Args:
        pdf_path:   Path to the source PDF file.
        output_dir: Root output directory (chunks land in
                    ``<output_dir>/processed/chunks/``).

    Returns:
        Absolute path to the written JSON file.

    Raises:
        FileNotFoundError: Propagated from parse_pdf() if the PDF is missing.
    """
    parsed = parse_pdf(pdf_path)
    chunked = chunk_contract(parsed)

    chunks_dir = os.path.join(output_dir, "processed", "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    output_path = os.path.join(chunks_dir, f"{chunked['contract_id']}.json")
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(chunked, fh, indent=2, ensure_ascii=False)

    logger.info(
        "Saved %d chunks for '%s' → %s",
        len(chunked["chunks"]),
        chunked["contract_id"],
        output_path,
    )
    return output_path
