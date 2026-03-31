import json
import logging
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

import config

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100  # ChromaDB add batch size


class ContractEmbedder:
    """Embeds contract chunks into ChromaDB using SentenceTransformers."""

    def __init__(self) -> None:
        logger.info("Loading SentenceTransformer '%s'...", config.EMBEDDING_MODEL)
        self.model = SentenceTransformer(config.EMBEDDING_MODEL)

        config.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(config.CHROMA_PERSIST_DIR))
        self.collection = self._client.get_or_create_collection(
            name="contracts",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB collection 'contracts' ready — %d items already indexed.",
            self.collection.count(),
        )

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def embed_all(self, chunks_dir: str) -> dict:
        """Embed every chunk from every JSON file in chunks_dir.

        Idempotent: chunks whose chunk_id is already in the collection
        are silently skipped.

        Returns
        -------
        {"total_embedded": int, "already_present": int}
        """
        chunks_path = Path(chunks_dir)
        all_chunks: list[dict] = []

        for json_file in sorted(chunks_path.glob("*.json")):
            with open(json_file, encoding="utf-8") as fh:
                data = json.load(fh)
            for chunk in data["chunks"]:
                all_chunks.append({
                    "chunk_id":    chunk["chunk_id"],
                    "text":        chunk["text"],
                    "contract_id": data["contract_id"],
                    "filename":    data["filename"],
                    "page_number": chunk.get("page_number", 0),
                })

        if not all_chunks:
            logger.warning("No chunk files found in %s", chunks_dir)
            return {"total_embedded": 0, "already_present": 0}

        # Idempotency — find which IDs are new
        all_ids = [c["chunk_id"] for c in all_chunks]
        existing_ids: set[str] = set(
            self.collection.get(ids=all_ids, include=[])["ids"]
        )
        to_add = [c for c in all_chunks if c["chunk_id"] not in existing_ids]
        already_present = len(existing_ids)

        if not to_add:
            logger.info("All %d chunks already indexed.", len(all_chunks))
            return {"total_embedded": 0, "already_present": already_present}

        # Embed and store in batches
        total_added = 0
        n_batches = (len(to_add) + _BATCH_SIZE - 1) // _BATCH_SIZE
        for batch_idx, i in enumerate(range(0, len(to_add), _BATCH_SIZE), 1):
            batch = to_add[i : i + _BATCH_SIZE]
            texts = [c["text"] for c in batch]
            embeddings = self.model.encode(texts, show_progress_bar=False).tolist()

            self.collection.add(
                ids=[c["chunk_id"] for c in batch],
                documents=texts,
                embeddings=embeddings,
                metadatas=[
                    {
                        "contract_id": c["contract_id"],
                        "filename":    c["filename"],
                        "page_number": c["page_number"],
                    }
                    for c in batch
                ],
            )
            total_added += len(batch)
            logger.debug("Batch %d/%d embedded (%d chunks)", batch_idx, n_batches, total_added)

        return {"total_embedded": total_added, "already_present": already_present}

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def query(self, question: str, n_results: int = 5) -> list[dict]:
        """Embed a question and return the top-n most similar contract chunks.

        Returns
        -------
        List of dicts: {chunk_id, contract_id, filename, page_number,
                        text, distance}
        """
        n = min(n_results, self.collection.count())
        if n == 0:
            logger.warning("Collection is empty — run embed_all() first.")
            return []

        embedding = self.model.encode(question).tolist()
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )

        output: list[dict] = []
        for chunk_id, doc, meta, dist in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({
                "chunk_id":    chunk_id,
                "contract_id": meta.get("contract_id", ""),
                "filename":    meta.get("filename", ""),
                "page_number": meta.get("page_number", 0),
                "text":        doc,
                "distance":    round(float(dist), 4),
            })
        return output
