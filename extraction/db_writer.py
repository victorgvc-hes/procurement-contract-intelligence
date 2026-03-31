import logging
from datetime import datetime, timezone

import duckdb

import config
from extraction.schema import ExtractionResult, PenaltyClause, PriceClause, RenewalClause

logger = logging.getLogger(__name__)


class DBWriter:
    def __init__(self) -> None:
        config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(config.DB_PATH))

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def init_schema(self) -> None:
        """Create all tables if they do not already exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                contract_id   TEXT PRIMARY KEY,
                filename      TEXT,
                processed_at  TIMESTAMP,
                total_chunks  INTEGER,
                clauses_found INTEGER
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS price_clauses (
                contract_id         TEXT,
                vendor_name         TEXT,
                clause_type         TEXT,
                source_text         TEXT,
                page_number         INTEGER,
                confidence          DOUBLE,
                unit_price          DOUBLE,
                currency            TEXT,
                unit_of_measure     TEXT,
                price_cap           DOUBLE,
                most_favored_nation BOOLEAN,
                extracted_at        TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS penalty_clauses (
                contract_id       TEXT,
                vendor_name       TEXT,
                clause_type       TEXT,
                source_text       TEXT,
                page_number       INTEGER,
                confidence        DOUBLE,
                trigger_condition TEXT,
                penalty_type      TEXT,
                penalty_value     DOUBLE,
                penalty_currency  TEXT,
                cap_on_liability  DOUBLE,
                extracted_at      TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS renewal_clauses (
                contract_id         TEXT,
                vendor_name         TEXT,
                clause_type         TEXT,
                source_text         TEXT,
                page_number         INTEGER,
                confidence          DOUBLE,
                initial_term_months INTEGER,
                renewal_type        TEXT,
                renewal_notice_days INTEGER,
                expiry_date         TEXT,
                max_renewals        INTEGER,
                extracted_at        TIMESTAMP
            )
        """)
        logger.info("DB schema ready at %s", config.DB_PATH)

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def write_result(self, result: ExtractionResult) -> None:
        """Insert (or replace) all clauses from an ExtractionResult.

        Deletes any pre-existing rows for contract_id first so the
        script is safe to re-run without creating duplicates.
        """
        now = datetime.now(timezone.utc)
        cid = result.contract_id

        # Idempotent: clear existing data for this contract
        for table in ("contracts", "price_clauses", "penalty_clauses", "renewal_clauses"):
            self.conn.execute(f"DELETE FROM {table} WHERE contract_id = ?", [cid])

        self.conn.execute(
            "INSERT INTO contracts VALUES (?, ?, ?, ?, ?)",
            [cid, result.filename, now, result.total_chunks_processed, len(result.clauses_found)],
        )

        for clause in result.clauses_found:
            if isinstance(clause, PriceClause):
                self.conn.execute(
                    "INSERT INTO price_clauses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        clause.contract_id, clause.vendor_name, clause.clause_type,
                        clause.source_text, clause.page_number, clause.confidence,
                        clause.unit_price, clause.currency, clause.unit_of_measure,
                        clause.price_cap, clause.most_favored_nation, now,
                    ],
                )
            elif isinstance(clause, PenaltyClause):
                self.conn.execute(
                    "INSERT INTO penalty_clauses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        clause.contract_id, clause.vendor_name, clause.clause_type,
                        clause.source_text, clause.page_number, clause.confidence,
                        clause.trigger_condition, clause.penalty_type, clause.penalty_value,
                        clause.penalty_currency, clause.cap_on_liability, now,
                    ],
                )
            elif isinstance(clause, RenewalClause):
                self.conn.execute(
                    "INSERT INTO renewal_clauses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        clause.contract_id, clause.vendor_name, clause.clause_type,
                        clause.source_text, clause.page_number, clause.confidence,
                        clause.initial_term_months, clause.renewal_type,
                        clause.renewal_notice_days, clause.expiry_date,
                        clause.max_renewals, now,
                    ],
                )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_summary(self) -> dict[str, int]:
        """Return row counts for every table."""
        tables = ["contracts", "price_clauses", "penalty_clauses", "renewal_clauses"]
        return {
            t: self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in tables
        }

    def close(self) -> None:
        self.conn.close()
