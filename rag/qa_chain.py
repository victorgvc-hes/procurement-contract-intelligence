import logging

import anthropic

import config
from rag.embedder import ContractEmbedder

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a procurement contract analyst. Answer the question using ONLY "
    "the contract excerpts provided. For each claim, cite the contract filename "
    "and page number. If the answer is not in the excerpts, say "
    "'Not found in the provided contracts'."
)


class ContractQA:
    """Retrieval-augmented Q&A over the contract corpus."""

    def __init__(self) -> None:
        self.embedder = ContractEmbedder()
        self.use_mock = config.USE_MOCK_EXTRACTOR
        self._client: anthropic.Anthropic | None = None
        if not self.use_mock:
            self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    # ------------------------------------------------------------------
    # Mock path
    # ------------------------------------------------------------------

    def mock_answer(self, question: str, context_chunks: list[dict]) -> dict:
        """Return a hardcoded but realistic-looking answer using retrieved metadata."""
        # Build a de-duped list of source filenames from the retrieved chunks
        seen: set[str] = set()
        unique_sources: list[dict] = []
        for c in context_chunks:
            if c["filename"] not in seen:
                seen.add(c["filename"])
                unique_sources.append(c)

        filenames = [s["filename"] for s in unique_sources[:3]]
        file_list = ", ".join(filenames) if filenames else "the contract corpus"

        q_lower = question.lower()
        if "penalt" in q_lower or "late deliver" in q_lower:
            answer_text = (
                f"[MOCK] Penalty clauses for late delivery were identified in multiple "
                f"contracts. Common structures include per-diem deductions (e.g. 1.5% of "
                f"invoice value per day after a 3-business-day grace period) and fixed "
                f"penalties per incident (e.g. $500 USD). Several agreements cap cumulative "
                f"liability at 10–15% of total contract value. "
                f"Relevant excerpts retrieved from: {file_list}."
            )
        elif "payment" in q_lower:
            answer_text = (
                f"[MOCK] Payment terms across the reviewed agreements vary from net-15 to "
                f"net-45 days from invoice receipt. Some contracts specify late-payment "
                f"interest at 1.5–2.0% per month, while shorter-term professional-services "
                f"engagements omit a late-fee clause entirely. "
                f"See excerpts from: {file_list}."
            )
        elif "expir" in q_lower or "renew" in q_lower:
            answer_text = (
                f"[MOCK] Several contracts contain renewal or expiry provisions. "
                f"Auto-renewal clauses with 60–90-day cancellation notice windows appear in "
                f"longer-term supply agreements, while fixed-term service contracts require "
                f"explicit mutual consent for extension. As of today, multiple contracts "
                f"have already passed their expiry dates. "
                f"Excerpts retrieved from: {file_list}."
            )
        else:
            answer_text = (
                f"[MOCK] Based on {len(context_chunks)} retrieved contract excerpts, a "
                f"direct answer to '{question}' was not determinable in mock mode. "
                f"Set USE_MOCK_EXTRACTOR=False and provide an API key for a Claude-generated "
                f"answer. Sources searched: {file_list}."
            )

        sources = [
            {"filename": c["filename"], "page_number": c["page_number"], "chunk_id": c["chunk_id"]}
            for c in context_chunks
        ]
        return {
            "question":         question,
            "answer":           answer_text,
            "sources":          sources,
            "chunks_retrieved": len(context_chunks),
        }

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def answer(self, question: str) -> dict:
        """Retrieve relevant chunks then answer using Claude (or mock).

        Returns
        -------
        {
            "question":         str,
            "answer":           str,
            "sources":          list[{filename, page_number, chunk_id}],
            "chunks_retrieved": int,
        }
        """
        context_chunks = self.embedder.query(question, n_results=5)

        if self.use_mock:
            return self.mock_answer(question, context_chunks)

        # Build context block for Claude
        context_text = "\n\n---\n\n".join(
            f"[Source: {c['filename']}, page {c['page_number']}]\n{c['text']}"
            for c in context_chunks
        )
        user_prompt = f"Question: {question}\n\nContract excerpts:\n{context_text}"

        response = self._client.messages.create(
            model=config.MODEL_NAME,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        answer_text = response.content[0].text.strip()

        sources = [
            {"filename": c["filename"], "page_number": c["page_number"], "chunk_id": c["chunk_id"]}
            for c in context_chunks
        ]
        return {
            "question":         question,
            "answer":           answer_text,
            "sources":          sources,
            "chunks_retrieved": len(context_chunks),
        }
