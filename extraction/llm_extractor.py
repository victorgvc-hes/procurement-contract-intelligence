import json
import logging

import anthropic

import config
from extraction.mock_extractor import get_mock_result
from extraction.schema import (
    ContractClause,
    ExtractionResult,
    PenaltyClause,
    PriceClause,
    RenewalClause,
)

logger = logging.getLogger(__name__)

# Keyword hints used to filter chunks before sending to the LLM.
# Chunks containing none of the hints for a clause type are skipped.
KEYWORD_HINTS: dict[str, list[str]] = {
    "price":   ["price", "cost", "fee", "payment", "rate", "tariff", "invoice", "amount"],
    "penalty": ["penalty", "liquidated", "damages", "breach", "default", "late", "failure to"],
    "renewal": ["renew", "renewal", "term", "expire", "expiry", "termination", "notice period"],
}

CLAUSE_MODELS: dict[str, type] = {
    "price":   PriceClause,
    "penalty": PenaltyClause,
    "renewal": RenewalClause,
}


class LLMExtractor:
    def __init__(self) -> None:
        self.use_mock: bool = config.USE_MOCK_EXTRACTOR
        self.model: str = config.MODEL_NAME
        self._client: anthropic.Anthropic | None = None
        if not self.use_mock:
            self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def extract(
        self,
        contract_id: str,
        chunks: list[dict],
        filename: str = "",
    ) -> ExtractionResult:
        """Extract structured clauses from a list of text chunks.

        Args:
            contract_id: Unique identifier for the contract.
            chunks:      Output of chunk_contract()["chunks"].
            filename:    Original PDF filename (used to populate ExtractionResult).

        Returns:
            ExtractionResult with all validated clauses found.
        """
        if self.use_mock:
            result = get_mock_result(contract_id)
            result.filename = filename or contract_id
            result.total_chunks_processed = len(chunks)
            return result

        return self._extract_with_llm(contract_id, chunks, filename or contract_id)

    # ------------------------------------------------------------------
    # Live LLM path
    # ------------------------------------------------------------------

    def _extract_with_llm(
        self,
        contract_id: str,
        chunks: list[dict],
        filename: str,
    ) -> ExtractionResult:
        all_clauses: list[ContractClause] = []
        errors: list[str] = []

        for clause_type, model_cls in CLAUSE_MODELS.items():
            keywords = KEYWORD_HINTS[clause_type]
            relevant = [
                c for c in chunks
                if any(kw in c["text"].lower() for kw in keywords)
            ]
            if not relevant:
                logger.debug("No relevant chunks for clause_type=%s in %s", clause_type, contract_id)
                continue

            schema_str = json.dumps(model_cls.model_json_schema(), indent=2)

            for chunk in relevant:
                try:
                    clauses = self._call_claude(
                        contract_id=contract_id,
                        clause_type=clause_type,
                        chunk=chunk,
                        schema_str=schema_str,
                        model_cls=model_cls,
                    )
                    all_clauses.extend(clauses)
                except Exception as exc:
                    msg = f"{chunk.get('chunk_id', '?')}: {exc}"
                    logger.warning("Extraction error — %s", msg)
                    errors.append(msg)

        return ExtractionResult(
            contract_id=contract_id,
            filename=filename,
            total_chunks_processed=len(chunks),
            clauses_found=all_clauses,
            extraction_errors=errors,
        )

    def _call_claude(
        self,
        contract_id: str,
        clause_type: str,
        chunk: dict,
        schema_str: str,
        model_cls: type,
    ) -> list[ContractClause]:
        system_prompt = (
            f"You are a procurement contract analyst. "
            f"Extract {clause_type} clauses only. "
            f"Return a JSON array of objects matching the schema below. "
            f"If no {clause_type} clause is present return an empty array []. "
            f"No other text.\n\nSchema:\n{schema_str}"
        )
        user_prompt = (
            f"contract_id: {contract_id}\n\n"
            f"Contract chunk (page {chunk.get('page_number', '?')}):\n"
            f"{chunk['text']}"
        )

        response = self._client.messages.create(
            model=self.model,
            max_tokens=config.MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw: str = response.content[0].text.strip()

        # Strip markdown code fences if Claude wraps the JSON
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        items: list[dict] = json.loads(raw)
        clauses: list[ContractClause] = []
        for item in items:
            # Inject required metadata that the LLM may omit
            item.setdefault("contract_id", contract_id)
            item.setdefault("vendor_name", contract_id)
            item.setdefault("source_text", chunk["text"][:500])
            item.setdefault("page_number", chunk.get("page_number"))
            item.setdefault("confidence", 0.8)
            item.setdefault("clause_type", clause_type)
            try:
                clauses.append(model_cls.model_validate(item))
            except Exception as exc:
                logger.warning("Pydantic validation failed: %s | item=%s", exc, item)
        return clauses
