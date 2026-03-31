"""
Deterministic mock extractor for development and testing.

Returns hardcoded ExtractionResult objects so the rest of the pipeline
can be exercised without consuming Claude API credits.
"""

from __future__ import annotations

from extraction.schema import (
    ExtractionResult,
    PenaltyClause,
    PriceClause,
    RenewalClause,
)

_MOCK_RESULTS: list[ExtractionResult] = [
    # ------------------------------------------------------------------
    # Contract 1 — goods supply agreement
    # ------------------------------------------------------------------
    ExtractionResult(
        contract_id="mock-001",
        filename="acme_supplies_2024.pdf",
        total_chunks_processed=12,
        clauses_found=[
            PriceClause(
                contract_id="mock-001",
                vendor_name="Acme Supplies LLC",
                source_text=(
                    "The unit price for each component shall be $4.75 USD per unit, "
                    "subject to a price cap of $6.00 per unit through contract expiry. "
                    "Vendor guarantees most-favored-nation pricing."
                ),
                page_number=3,
                confidence=0.95,
                unit_price=4.75,
                currency="USD",
                unit_of_measure="per unit",
                price_cap=6.00,
                most_favored_nation=True,
            ),
            PenaltyClause(
                contract_id="mock-001",
                vendor_name="Acme Supplies LLC",
                source_text=(
                    "In the event of late delivery exceeding three (3) business days, "
                    "Vendor shall pay a penalty of 1.5% of the invoice value per day, "
                    "capped at 10% of the total order value."
                ),
                page_number=7,
                confidence=0.92,
                trigger_condition="late delivery > 3 business days",
                penalty_type="per_diem",
                penalty_value=1.5,
                penalty_currency="USD",
                cap_on_liability=10.0,
            ),
            RenewalClause(
                contract_id="mock-001",
                vendor_name="Acme Supplies LLC",
                source_text=(
                    "This Agreement has an initial term of twelve (12) months and "
                    "automatically renews for successive one-year periods unless either "
                    "party provides sixty (60) days written notice of non-renewal."
                ),
                page_number=11,
                confidence=0.97,
                initial_term_months=12,
                renewal_type="auto",
                renewal_notice_days=60,
                expiry_date="2025-12-31",
                max_renewals=None,
            ),
        ],
    ),
    # ------------------------------------------------------------------
    # Contract 2 — logistics services
    # ------------------------------------------------------------------
    ExtractionResult(
        contract_id="mock-002",
        filename="global_logistics_2024.pdf",
        total_chunks_processed=18,
        clauses_found=[
            PriceClause(
                contract_id="mock-002",
                vendor_name="Global Logistics Partners",
                source_text=(
                    "Freight charges are set at $320.00 USD per shipment for standard lanes. "
                    "No price cap applies. MFN pricing is not guaranteed."
                ),
                page_number=2,
                confidence=0.88,
                unit_price=320.00,
                currency="USD",
                unit_of_measure="per shipment",
                price_cap=None,
                most_favored_nation=False,
            ),
            PenaltyClause(
                contract_id="mock-002",
                vendor_name="Global Logistics Partners",
                source_text=(
                    "Failure to deliver within the agreed transit window shall result in "
                    "a fixed penalty of $500 USD per incident, with no cap on cumulative liability."
                ),
                page_number=9,
                confidence=0.85,
                trigger_condition="delivery outside agreed transit window",
                penalty_type="fixed",
                penalty_value=500.00,
                penalty_currency="USD",
                cap_on_liability=None,
            ),
            RenewalClause(
                contract_id="mock-002",
                vendor_name="Global Logistics Partners",
                source_text=(
                    "Contract runs for twenty-four (24) months. Renewal requires mutual "
                    "written agreement no later than ninety (90) days before expiry. "
                    "Maximum of two (2) renewals permitted."
                ),
                page_number=15,
                confidence=0.91,
                initial_term_months=24,
                renewal_type="manual",
                renewal_notice_days=90,
                expiry_date="2026-03-14",
                max_renewals=2,
            ),
        ],
    ),
    # ------------------------------------------------------------------
    # Contract 3 — professional services
    # ------------------------------------------------------------------
    ExtractionResult(
        contract_id="mock-003",
        filename="techpro_solutions_2024.pdf",
        total_chunks_processed=9,
        clauses_found=[
            PriceClause(
                contract_id="mock-003",
                vendor_name="TechPro Solutions Inc.",
                source_text=(
                    "Services are billed at $185.00 USD per hour. No price cap or "
                    "most-favored-nation clause is included in this agreement."
                ),
                page_number=1,
                confidence=0.99,
                unit_price=185.00,
                currency="USD",
                unit_of_measure="per hour",
                price_cap=None,
                most_favored_nation=False,
            ),
            PenaltyClause(
                contract_id="mock-003",
                vendor_name="TechPro Solutions Inc.",
                source_text=(
                    "If deliverables are not submitted by the agreed milestone date, "
                    "a deduction of 5% of the milestone value shall apply, "
                    "capped at 15% of the total contract value."
                ),
                page_number=4,
                confidence=0.87,
                trigger_condition="deliverable not submitted by milestone date",
                penalty_type="percentage",
                penalty_value=5.0,
                penalty_currency="USD",
                cap_on_liability=15.0,
            ),
            RenewalClause(
                contract_id="mock-003",
                vendor_name="TechPro Solutions Inc.",
                source_text=(
                    "This is a fixed-term engagement of six (6) months with no automatic "
                    "renewal. Extension requires a new statement of work."
                ),
                page_number=6,
                confidence=0.96,
                initial_term_months=6,
                renewal_type="manual",
                renewal_notice_days=None,
                expiry_date="2024-11-30",
                max_renewals=0,
            ),
        ],
    ),
]


def get_mock_result(contract_id: str) -> ExtractionResult:
    """Return a deterministic mock ExtractionResult for the given contract ID."""
    template = _MOCK_RESULTS[hash(contract_id) % len(_MOCK_RESULTS)]
    result = template.model_copy(deep=True)
    result.contract_id = contract_id
    for clause in result.clauses_found:
        clause.contract_id = contract_id
    return result


def get_all_mock_results() -> list[ExtractionResult]:
    """Return all three hardcoded mock ExtractionResult objects."""
    return list(_MOCK_RESULTS)
