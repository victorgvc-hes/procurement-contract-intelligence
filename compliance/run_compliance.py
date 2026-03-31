"""
Compliance gap report — runs all three GapEngine checks and saves CSVs.

Usage:
    python compliance/run_compliance.py
"""

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config
from compliance.gap_engine import GapEngine

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

OUTPUT_DIR = config.DATA_DIR / "processed"


def _save(df, name: str) -> Path:
    path = OUTPUT_DIR / f"compliance_{name}.csv"
    df.to_csv(path, index=False)
    return path


def _section(title: str, n: int) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}  --  {n} finding(s)")
    print(f"{'='*60}")


def main() -> None:
    engine = GapEngine()

    # ------------------------------------------------------------------
    # 1. Price breaches
    # ------------------------------------------------------------------
    price_df = engine.price_gaps()
    _section("PRICE BREACHES", len(price_df))
    if price_df.empty:
        print("  No price breaches detected.")
        print("  (With mock extraction, vendor names don't match SCMS suppliers.")
        print("   Enable live extraction to see real matches.)")
    else:
        print(price_df.to_string(index=False))
    path = _save(price_df, "price_breaches")
    print(f"\n  Saved -> {path}")

    # ------------------------------------------------------------------
    # 2. Penalty exposure
    # ------------------------------------------------------------------
    penalty_df = engine.penalty_exposure()
    _section("PENALTY EXPOSURE", len(penalty_df))
    if penalty_df.empty:
        print("  No penalty exposure detected.")
        print("  (With mock extraction, vendor names don't match SCMS suppliers.")
        print("   Enable live extraction to see real matches.)")
    else:
        print(penalty_df.to_string(index=False))
    path = _save(penalty_df, "penalty_exposure")
    print(f"\n  Saved -> {path}")

    # ------------------------------------------------------------------
    # 3. Renewal alerts
    # ------------------------------------------------------------------
    renewal_df = engine.renewal_alerts()
    _section("RENEWAL ALERTS", len(renewal_df))
    if renewal_df.empty:
        print("  No renewal alerts.")
    else:
        # Group output by status for readability
        for status in ("expired", "urgent", "upcoming"):
            sub = renewal_df[renewal_df["status"] == status]
            if sub.empty:
                continue
            print(f"\n  [{status.upper()}] ({len(sub)} contract(s))")
            print(
                sub[["vendor_name", "contract_id", "expiry_date",
                     "days_until_expiry", "renewal_type", "notice_days_required"]]
                .to_string(index=False)
            )
    path = _save(renewal_df, "renewal_alerts")
    print(f"\n  Saved -> {path}")

    engine.close()

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    print(f"  Price breaches   : {len(price_df)}")
    print(f"  Penalty exposure : {len(penalty_df)}")
    print(f"  Renewal alerts   : {len(renewal_df)}")
    print(f"    expired  : {(renewal_df['status'] == 'expired').sum() if not renewal_df.empty else 0}")
    print(f"    urgent   : {(renewal_df['status'] == 'urgent').sum() if not renewal_df.empty else 0}")
    print(f"    upcoming : {(renewal_df['status'] == 'upcoming').sum() if not renewal_df.empty else 0}")


if __name__ == "__main__":
    main()
