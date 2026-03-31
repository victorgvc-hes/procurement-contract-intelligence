from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date

class BaseClause(BaseModel):
    contract_id: str
    vendor_name: str
    clause_type: str
    source_text: str           # verbatim chunk the extraction came from
    page_number: Optional[int]
    confidence: float = Field(ge=0.0, le=1.0)

class PriceClause(BaseClause):
    clause_type: Literal["price"] = "price"
    unit_price: Optional[float]
    currency: str = "USD"
    unit_of_measure: Optional[str]   # e.g. "per unit", "per kg", "per shipment"
    price_cap: Optional[float]
    most_favored_nation: bool = False # MFN clause present?

class PenaltyClause(BaseClause):
    clause_type: Literal["penalty"] = "penalty"
    trigger_condition: str           # e.g. "late delivery > 3 days"
    penalty_type: Literal["fixed", "percentage", "per_diem", "unspecified"]
    penalty_value: Optional[float]
    penalty_currency: str = "USD"
    cap_on_liability: Optional[float]

class RenewalClause(BaseClause):
    clause_type: Literal["renewal"] = "renewal"
    initial_term_months: Optional[int]
    renewal_type: Literal["auto", "manual", "evergreen", "unspecified"]
    renewal_notice_days: Optional[int]  # days notice required to cancel/renew
    expiry_date: Optional[str]
    max_renewals: Optional[int]

# Union type used throughout the pipeline
ContractClause = PriceClause | PenaltyClause | RenewalClause

class ExtractionResult(BaseModel):
    contract_id: str
    filename: str
    total_chunks_processed: int
    clauses_found: list[ContractClause]
    extraction_errors: list[str] = []
