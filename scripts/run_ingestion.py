"""
Batch ingestion script — processes all PDFs in data/raw/contracts/.

Usage:
    python scripts/run_ingestion.py
"""

import json
import sys
from pathlib import Path

# Ensure project root is on sys.path regardless of where the script is called from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.pipeline import run_pipeline

CONTRACTS_DIR = PROJECT_ROOT / "data" / "raw" / "contracts"
OUTPUT_DIR = PROJECT_ROOT / "data"


def main() -> None:
    pdf_files = sorted(CONTRACTS_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {CONTRACTS_DIR}")
        sys.exit(1)

    total_chunks = 0
    processed = 0

    for pdf_path in pdf_files:
        try:
            output_path = run_pipeline(str(pdf_path), str(OUTPUT_DIR))
            with open(output_path, encoding="utf-8") as fh:
                data = json.load(fh)
            n_chunks = len(data["chunks"])
            total_chunks += n_chunks
            processed += 1
            print(f"Processed {pdf_path.name} -> {n_chunks} chunks")
        except Exception as exc:
            print(f"ERROR {pdf_path.name}: {exc}")

    print(f"\nTotal: {processed} contracts, {total_chunks} chunks")


if __name__ == "__main__":
    main()
