import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

import config

st.set_page_config(
    page_title="Contract Explorer · Contract Intelligence",
    page_icon="📑",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📄 Contract Intelligence")
    mode = "🟡 Mock Mode" if config.USE_MOCK_EXTRACTOR else "🟢 Live Mode"
    st.markdown(f"**{mode}**")
    st.divider()
    st.divider()
    st.caption("Built with Claude API · CUAD Dataset")


# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_resource
def _conn():
    return duckdb.connect(str(config.DB_PATH), read_only=True)


@st.cache_data(ttl=120)
def _load_contracts() -> pd.DataFrame:
    return _conn().execute("""
        SELECT contract_id,
               filename,
               clauses_found,
               CAST(processed_at AS VARCHAR) AS processed_at
        FROM contracts
        ORDER BY filename
    """).df()


@st.cache_data(ttl=120)
def _load_clauses(contract_id: str) -> dict[str, pd.DataFrame]:
    conn = _conn()
    price = conn.execute(
        "SELECT vendor_name, unit_price, currency, unit_of_measure, "
        "       price_cap, most_favored_nation, confidence, page_number "
        "FROM price_clauses WHERE contract_id = ?", [contract_id]
    ).df()
    penalty = conn.execute(
        "SELECT vendor_name, trigger_condition, penalty_type, penalty_value, "
        "       penalty_currency, cap_on_liability, confidence, page_number "
        "FROM penalty_clauses WHERE contract_id = ?", [contract_id]
    ).df()
    renewal = conn.execute(
        "SELECT vendor_name, renewal_type, initial_term_months, renewal_notice_days, "
        "       expiry_date, max_renewals, confidence, page_number "
        "FROM renewal_clauses WHERE contract_id = ?", [contract_id]
    ).df()
    return {"Price": price, "Penalty": penalty, "Renewal": renewal}


# ── Main ──────────────────────────────────────────────────────────────────────
st.title("📑 Contract Explorer")
st.markdown("Browse extracted contracts and drill into individual clause details.")

try:
    all_contracts = _load_contracts()

    # ── Sidebar filter ────────────────────────────────────────────────────────
    all_filenames = sorted(all_contracts["filename"].tolist())
    selected_files = st.sidebar.multiselect(
        "Filter by filename",
        options=all_filenames,
        placeholder="All contracts",
    )
    filtered = (
        all_contracts[all_contracts["filename"].isin(selected_files)]
        if selected_files else all_contracts
    )

    st.markdown(
        f"**{len(filtered)}** contract(s) shown"
        + (f" (filtered from {len(all_contracts)})" if selected_files else "")
    )

    # ── Contracts table with row selection ───────────────────────────────────
    selection = st.dataframe(
        filtered.reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "contract_id":   st.column_config.TextColumn("Contract ID", width="medium"),
            "filename":      st.column_config.TextColumn("Filename",    width="large"),
            "clauses_found": st.column_config.NumberColumn("Clauses",   width="small"),
            "processed_at":  st.column_config.TextColumn("Processed",   width="medium"),
        },
    )

    # ── Detail panel ─────────────────────────────────────────────────────────
    rows = selection.selection.rows
    if rows:
        contract_id = filtered.reset_index(drop=True).iloc[rows[0]]["contract_id"]
        filename    = filtered.reset_index(drop=True).iloc[rows[0]]["filename"]

        st.divider()
        st.subheader(f"📄 {filename}")

        clauses = _load_clauses(contract_id)
        total_by_type = {t: len(df) for t, df in clauses.items()}

        # Clause breakdown chart
        chart_df = pd.DataFrame({
            "Type": list(total_by_type.keys()),
            "Clauses": list(total_by_type.values()),
        })
        fig = px.bar(
            chart_df, x="Type", y="Clauses", color="Type", text="Clauses",
            color_discrete_map={
                "Price":   "#3B82F6",
                "Penalty": "#EF4444",
                "Renewal": "#10B981",
            },
            title="Clause Count by Type",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, height=280,
                          margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

        # Per-type sub-tables in an expander
        with st.expander("📋 Extracted Clauses", expanded=True):
            tabs = st.tabs(["💰 Price", "⚡ Penalty", "🔄 Renewal"])
            for tab, (clause_type, df) in zip(tabs, clauses.items()):
                with tab:
                    if df.empty:
                        st.info(f"No {clause_type.lower()} clauses found for this contract.")
                    else:
                        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("👆 Click a row to view its extracted clauses.")

except Exception as exc:
    st.warning("⚠️ Database not ready — run the extraction pipeline first.")
    with st.expander("Error details"):
        st.exception(exc)
