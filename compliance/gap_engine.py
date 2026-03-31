import logging
from datetime import date, timedelta

import duckdb
import pandas as pd

import config
from compliance.po_loader import load_pos

logger = logging.getLogger(__name__)


class GapEngine:
    """Joins extracted contract clauses against PO actuals to surface gaps."""

    def __init__(self) -> None:
        self.conn = duckdb.connect(str(config.DB_PATH), read_only=True)
        self.pos = load_pos()

    # ------------------------------------------------------------------
    # 1. Price breaches
    # ------------------------------------------------------------------

    def price_gaps(self) -> pd.DataFrame:
        """Return vendors where actual avg unit price exceeds contracted price
        by more than PRICE_BREACH_THRESHOLD (default 5%).

        Join strategy: case-insensitive substring match between
        price_clauses.vendor_name and PO vendor strings, to handle
        naming variations between contract text and PO records.

        Returns
        -------
        pd.DataFrame columns:
            vendor_name, contracted_price, actual_avg_price,
            gap_pct, po_count, breach
        """
        clauses = self.conn.execute(
            "SELECT vendor_name, unit_price AS contracted_price FROM price_clauses"
        ).df()

        if clauses.empty or self.pos.empty:
            return pd.DataFrame(columns=[
                "vendor_name", "contracted_price", "actual_avg_price",
                "gap_pct", "po_count", "breach",
            ])

        po_agg = (
            self.pos.groupby("vendor")["unit_price"]
            .agg(actual_avg_price="mean", po_count="count")
            .reset_index()
            .rename(columns={"vendor": "vendor_name"})
        )

        # Fuzzy join: clause vendor matches PO vendor if either string contains
        # the other (case-insensitive). We keep the best (first) match.
        rows = []
        for _, clause in clauses.iterrows():
            cname = clause["vendor_name"].lower()
            match = po_agg[
                po_agg["vendor_name"].str.lower().str.contains(cname, regex=False)
                | pd.Series(
                    [cname in v.lower() for v in po_agg["vendor_name"]],
                    index=po_agg.index,
                )
            ]
            if match.empty:
                continue
            for _, po_row in match.iterrows():
                rows.append({
                    "vendor_name":       clause["vendor_name"],
                    "contracted_price":  clause["contracted_price"],
                    "actual_avg_price":  po_row["actual_avg_price"],
                    "po_count":          po_row["po_count"],
                })

        if not rows:
            return pd.DataFrame(columns=[
                "vendor_name", "contracted_price", "actual_avg_price",
                "gap_pct", "po_count", "breach",
            ])

        result = pd.DataFrame(rows)
        result["gap_pct"] = (
            (result["actual_avg_price"] - result["contracted_price"])
            / result["contracted_price"].replace(0, float("nan"))
        )
        threshold = config.PRICE_BREACH_THRESHOLD
        result = result[result["gap_pct"] > threshold].copy()
        result["breach"] = True
        result["gap_pct"] = result["gap_pct"].round(4)
        result["actual_avg_price"] = result["actual_avg_price"].round(4)
        return result.reset_index(drop=True)

    # ------------------------------------------------------------------
    # 2. Penalty exposure
    # ------------------------------------------------------------------

    def penalty_exposure(self) -> pd.DataFrame:
        """Return vendors with a penalty clause that also have late POs.

        Estimated exposure = late_po_count * penalty_value (for fixed / per_diem)
        or left as NaN for percentage-type penalties (no contract value available).

        Returns
        -------
        pd.DataFrame columns:
            vendor_name, late_po_count, avg_days_late,
            penalty_value, penalty_type, estimated_exposure
        """
        clauses = self.conn.execute(
            """SELECT vendor_name, penalty_value, penalty_type
               FROM penalty_clauses"""
        ).df()

        late_pos = self.pos[self.pos["lead_time_delta_days"] > 0].copy()

        late_agg = (
            late_pos.groupby("vendor")["lead_time_delta_days"]
            .agg(late_po_count="count", avg_days_late="mean")
            .reset_index()
            .rename(columns={"vendor": "vendor_name"})
        )

        rows = []
        for _, clause in clauses.iterrows():
            cname = clause["vendor_name"].lower()
            match = late_agg[
                late_agg["vendor_name"].str.lower().str.contains(cname, regex=False)
                | pd.Series(
                    [cname in v.lower() for v in late_agg["vendor_name"]],
                    index=late_agg.index,
                )
            ]
            if match.empty:
                continue
            for _, po_row in match.iterrows():
                pval = clause["penalty_value"]
                ptype = clause["penalty_type"]
                if ptype in ("fixed", "per_diem") and pd.notna(pval):
                    exposure = po_row["late_po_count"] * pval
                else:
                    exposure = float("nan")
                rows.append({
                    "vendor_name":       clause["vendor_name"],
                    "late_po_count":     int(po_row["late_po_count"]),
                    "avg_days_late":     round(po_row["avg_days_late"], 1),
                    "penalty_value":     pval,
                    "penalty_type":      ptype,
                    "estimated_exposure": exposure,
                })

        if not rows:
            return pd.DataFrame(columns=[
                "vendor_name", "late_po_count", "avg_days_late",
                "penalty_value", "penalty_type", "estimated_exposure",
            ])
        return pd.DataFrame(rows).reset_index(drop=True)

    # ------------------------------------------------------------------
    # 3. Renewal alerts
    # ------------------------------------------------------------------

    def renewal_alerts(self) -> pd.DataFrame:
        """Return renewal clauses expiring within RENEWAL_ALERT_DAYS days
        (or already expired).

        Status labels
        -------------
        'expired'  — expiry_date is in the past
        'urgent'   — expires within 30 days
        'upcoming' — expires within RENEWAL_ALERT_DAYS days

        Returns
        -------
        pd.DataFrame columns:
            vendor_name, contract_id, expiry_date, days_until_expiry,
            renewal_type, notice_days_required, status
        """
        clauses = self.conn.execute(
            """SELECT vendor_name, contract_id, expiry_date,
                      renewal_type, renewal_notice_days
               FROM renewal_clauses
               WHERE expiry_date IS NOT NULL"""
        ).df()

        if clauses.empty:
            return pd.DataFrame(columns=[
                "vendor_name", "contract_id", "expiry_date", "days_until_expiry",
                "renewal_type", "notice_days_required", "status",
            ])

        clauses["expiry_date"] = pd.to_datetime(clauses["expiry_date"], errors="coerce")
        today = pd.Timestamp(date.today())
        alert_cutoff = today + pd.Timedelta(days=config.RENEWAL_ALERT_DAYS)

        alerts = clauses[clauses["expiry_date"] <= alert_cutoff].copy()
        alerts["days_until_expiry"] = (alerts["expiry_date"] - today).dt.days

        def _status(days: float) -> str:
            if days < 0:
                return "expired"
            if days <= 30:
                return "urgent"
            return "upcoming"

        alerts["status"] = alerts["days_until_expiry"].apply(_status)
        alerts = alerts.rename(columns={"renewal_notice_days": "notice_days_required"})
        alerts["expiry_date"] = alerts["expiry_date"].dt.date.astype(str)
        return alerts[
            ["vendor_name", "contract_id", "expiry_date", "days_until_expiry",
             "renewal_type", "notice_days_required", "status"]
        ].reset_index(drop=True)

    def close(self) -> None:
        self.conn.close()
