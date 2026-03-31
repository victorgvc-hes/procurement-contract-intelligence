"""
RAG pipeline runner — embeds all contracts then answers 3 test questions.

Usage:
    python rag/run_rag.py
"""

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config
from rag.embedder import ContractEmbedder
from rag.qa_chain import ContractQA

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

TEST_QUESTIONS = [
    "Which contracts mention penalties for late delivery?",
    "What are the payment terms in the agreements?",
    "Which contracts are expiring or up for renewal?",
]


def main() -> None:
    # ------------------------------------------------------------------
    # Phase 1: embed all contract chunks
    # ------------------------------------------------------------------
    print("=" * 64)
    print("  EMBEDDING CONTRACTS")
    print("=" * 64)

    embedder = ContractEmbedder()
    summary = embedder.embed_all(str(config.CHUNKS_DIR))

    print(f"  Chunks embedded this run  : {summary['total_embedded']}")
    print(f"  Chunks already present    : {summary['already_present']}")
    print(f"  Total collection size     : {embedder.collection.count()} chunks")

    # ------------------------------------------------------------------
    # Phase 2: answer test questions
    # ------------------------------------------------------------------
    print("\n" + "=" * 64)
    print("  CONTRACT Q&A  (mock mode)" if config.USE_MOCK_EXTRACTOR else "  CONTRACT Q&A  (live Claude)")
    print("=" * 64)

    qa = ContractQA()

    for i, question in enumerate(TEST_QUESTIONS, 1):
        result = qa.answer(question)

        print(f"\nQ{i}: {result['question']}")
        print("-" * 64)
        print(f"Answer:\n{result['answer']}")
        print(f"\nTop sources  ({result['chunks_retrieved']} chunks retrieved):")
        for src in result["sources"][:3]:
            print(f"  [{src['chunk_id']}]")
            print(f"    file : {src['filename']}")
            print(f"    page : {src['page_number']}")


if __name__ == "__main__":
    main()
