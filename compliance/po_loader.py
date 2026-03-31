import re
import logging

import pandas as pd

import config

logger = logging.getLogger(__name__)


def _to_snake(col: str) -> str:
    """Convert an arbitrary column name to snake_case.

    E.g. 'Unit of Measure (Per Pack)' -> 'unit_of_measure_per_pack'
         'PO / SO #'                  -> 'po_so'
    """
    col = col.lower()
    col = re.sub(r"[^a-z0-9]+", "_", col)   # non-alphanumeric -> _
    col = col.strip("_")
    return col


def load_pos() -> pd.DataFrame:
    """Load and clean the SCMS purchase-order dataset.

    Returns
    -------
    pd.DataFrame with standardised column names, parsed date columns,
    a computed ``lead_time_delta_days`` column, and vendor-null rows removed.

    Key columns after cleaning
    --------------------------
    vendor                    : supplier / vendor name
    unit_price                : unit price (USD)
    scheduled_delivery_date   : planned delivery date (datetime)
    delivered_to_client_date  : actual delivery date (datetime)
    lead_time_delta_days      : actual minus scheduled in days
                                (positive = late, negative = early)
    """
    df = pd.read_csv(config.PO_CSV, low_memory=False)
    logger.info("Loaded %d rows from %s", len(df), config.PO_CSV.name)

    # Standardise column names
    df.columns = [_to_snake(c) for c in df.columns]

    # Parse date columns — coerce unparseable strings (e.g. "Date Not Captured") to NaT
    date_cols = ["scheduled_delivery_date", "delivered_to_client_date"]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], format="%d-%b-%y", errors="coerce")

    # Computed delivery delta (positive = late)
    df["lead_time_delta_days"] = (
        df["delivered_to_client_date"] - df["scheduled_delivery_date"]
    ).dt.days

    # Drop rows with no vendor name
    before = len(df)
    df = df.dropna(subset=["vendor"])
    dropped = before - len(df)
    if dropped:
        logger.warning("Dropped %d rows with null vendor", dropped)

    logger.info(
        "PO dataset ready: %d rows, %d late deliveries",
        len(df),
        (df["lead_time_delta_days"] > 0).sum(),
    )
    return df.reset_index(drop=True)
