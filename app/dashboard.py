import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

import config

st.set_page_config(
    page_title="Contract Intelligence",
    page_icon="📄",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📄 Contract Intelligence")
    if config.USE_MOCK_EXTRACTOR:
        st.markdown("🟡 **Mock Mode**  \n*No API credits consumed*")
    else:
        st.markdown("🟢 **Live Mode**  \n*Using Claude API*")
    st.divider()
    st.divider()
    st.caption("Built with Claude API · CUAD Dataset")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📄 Contract Intelligence")
st.markdown(
    "AI-powered extraction, compliance monitoring, and semantic search "
    "across your procurement contract corpus."
)
st.divider()


# ── Data helpers ──────────────────────────────────────────────────────────────
@st.cache_resource
def _conn():
    return duckdb.connect(str(config.DB_PATH), read_only=True)


@st.cache_data(ttl=120)
def _load_metrics():
    conn = _conn()
    total   = conn.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
    price   = conn.execute("SELECT COUNT(*) FROM price_clauses").fetchone()[0]
    penalty = conn.execute("SELECT COUNT(*) FROM penalty_clauses").fetchone()[0]
    renewal = conn.execute("SELECT COUNT(*) FROM renewal_clauses").fetchone()[0]
    cutoff  = (date.today() + timedelta(days=config.RENEWAL_ALERT_DAYS)).isoformat()
    expiring = conn.execute(
        "SELECT COUNT(*) FROM renewal_clauses "
        "WHERE expiry_date IS NOT NULL AND expiry_date <= ?",
        [cutoff],
    ).fetchone()[0]
    return {
        "total_contracts": total,
        "price": price, "penalty": penalty, "renewal": renewal,
        "total_clauses": price + penalty + renewal,
        "expiring": expiring,
    }


@st.cache_data(ttl=120)
def _recent_contracts(limit: int = 10):
    return _conn().execute(f"""
        SELECT contract_id,
               filename,
               clauses_found,
               CAST(processed_at AS VARCHAR) AS processed_at
        FROM contracts
        ORDER BY processed_at DESC
        LIMIT {limit}
    """).df()


# ── Layout ────────────────────────────────────────────────────────────────────
try:
    m = _load_metrics()

    # Metric cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Contracts Processed", f"{m['total_contracts']:,}")
    c2.metric("Clauses Extracted",   f"{m['total_clauses']:,}")
    c3.metric("Compliance Alerts",   f"{m['expiring']:,}",
              help="Contracts expiring or already expired")
    c4.metric(f"Expiring ≤ {config.RENEWAL_ALERT_DAYS} days", f"{m['expiring']:,}")

    st.divider()

    left, right = st.columns([1, 2], gap="large")

    with left:
        st.subheader("Clause Breakdown")
        clause_df = pd.DataFrame({
            "Type":  ["Price", "Penalty", "Renewal"],
            "Count": [m["price"], m["penalty"], m["renewal"]],
        })
        fig = px.bar(
            clause_df, x="Type", y="Count", color="Type", text="Count",
            color_discrete_map={
                "Price":   "#3B82F6",
                "Penalty": "#EF4444",
                "Renewal": "#10B981",
            },
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, height=340,
                          margin=dict(t=20, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Recently Processed Contracts")
        st.dataframe(
            _recent_contracts(),
            use_container_width=True,
            hide_index=True,
            column_config={
                "contract_id":   st.column_config.TextColumn("Contract ID", width="medium"),
                "filename":      st.column_config.TextColumn("Filename",    width="large"),
                "clauses_found": st.column_config.NumberColumn("Clauses",   width="small"),
                "processed_at":  st.column_config.TextColumn("Processed",   width="medium"),
            },
        )

except Exception as exc:
    st.warning("⚠️ Database not ready — run the extraction pipeline first.")
    st.code("python extraction/run_extraction.py", language="bash")
    with st.expander("Error details"):
        st.exception(exc)
