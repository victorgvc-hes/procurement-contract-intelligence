"""
Batch extraction script — runs LLM extraction on all chunked contracts
and writes results to DuckDB.

Usage:
    python extraction/run_extraction.py
"""

import json
import logging
import sys
from pathlib import Path

# Ensure project root is importable regardless of invocation directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config
from extraction.db_writer import DBWriter
from extraction.llm_extractor import LLMExtractor

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    chunk_files = sorted(config.CHUNKS_DIR.glob("*.json"))
    if not chunk_files:
        print(f"No chunk files found in {config.CHUNKS_DIR}")
        sys.exit(1)

    db = DBWriter()
    db.init_schema()
    extractor = LLMExtractor()

    for chunk_file in chunk_files:
        with open(chunk_file, encoding="utf-8") as fh:
            data = json.load(fh)

        contract_id: str = data["contract_id"]
        filename: str = data["filename"]
        chunks: list[dict] = data["chunks"]

        result = extractor.extract(contract_id, chunks, filename=filename)
        db.write_result(result)

        price   = sum(1 for c in result.clauses_found if c.clause_type == "price")
        penalty = sum(1 for c in result.clauses_found if c.clause_type == "penalty")
        renewal = sum(1 for c in result.clauses_found if c.clause_type == "renewal")
        total   = len(result.clauses_found)

        print(
            f"{contract_id}: {total} clauses extracted "
            f"(price={price}, penalty={penalty}, renewal={renewal})"
        )

    summary = db.get_summary()
    print("\nDatabase summary:")
    for table, count in summary.items():
        print(f"  {table:<22} {count} rows")

    db.close()


if __name__ == "__main__":
    main()
