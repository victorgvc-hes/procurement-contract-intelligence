import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

import config

st.set_page_config(
    page_title="Compliance Gaps · Contract Intelligence",
    page_icon="⚠️",
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
def _get_engine():
    from compliance.gap_engine import GapEngine
    return GapEngine()


@st.cache_data(ttl=120)
def _price_gaps() -> pd.DataFrame:
    return _get_engine().price_gaps()


@st.cache_data(ttl=120)
def _penalty_exposure() -> pd.DataFrame:
    return _get_engine().penalty_exposure()


@st.cache_data(ttl=120)
def _renewal_alerts() -> pd.DataFrame:
    return _get_engine().renewal_alerts()


# ── Helpers ───────────────────────────────────────────────────────────────────
_MOCK_NOTE = (
    "**Running in Mock Mode** — vendor names in extracted clauses are fictional "
    "('Acme Supplies LLC', 'Global Logistics Partners', etc.) and do not match "
    "SCMS pharmaceutical supplier names.  \n"
    "Set `USE_MOCK_EXTRACTOR = False` in `config.py` and add your Anthropic API key "
    "to run live extraction and generate real vendor-matched compliance findings."
)

_STATUS_COLORS = {
    "expired":  "#fca5a5",   # red-300
    "urgent":   "#fdba74",   # orange-300
    "upcoming": "#fde047",   # yellow-300
}


def _style_status(val: str) -> str:
    bg = _STATUS_COLORS.get(val, "")
    return f"background-color: {bg}; font-weight: bold;" if bg else ""


# ── Main ──────────────────────────────────────────────────────────────────────
st.title("⚠️ Compliance Gaps")
st.markdown(
    "Surface price breaches, penalty exposure, and renewal deadlines "
    "by joining extracted contract clauses against PO actuals."
)

tab_price, tab_penalty, tab_renewal = st.tabs(
    ["💰 Price Breaches", "⚡ Penalty Exposure", "🔄 Renewal Alerts"]
)

# ── Tab 1: Price Breaches ─────────────────────────────────────────────────────
with tab_price:
    st.subheader("Price Breaches")
    st.markdown(
        f"Vendors where the average PO unit price exceeds the contracted price "
        f"by more than **{config.PRICE_BREACH_THRESHOLD * 100:.0f}%**."
    )
    try:
        price_df = _price_gaps()
        if price_df.empty:
            st.info("ℹ️ No price breaches detected.")
            if config.USE_MOCK_EXTRACTOR:
                st.markdown(_MOCK_NOTE)
        else:
            n = len(price_df)
            st.metric("Breaches Found", n)
            st.dataframe(
                price_df.style.format({"gap_pct": "{:.1%}", "actual_avg_price": "{:.4f}",
                                       "contracted_price": "{:.4f}"}),
                use_container_width=True, hide_index=True,
            )
            fig = px.bar(
                price_df, x="vendor_name", y="gap_pct",
                color_discrete_sequence=["#EF4444"],
                labels={"gap_pct": "Price Gap (%)", "vendor_name": "Vendor"},
                title="Price Gap vs Contract — by Vendor",
                text=price_df["gap_pct"].map("{:.1%}".format),
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(height=360, margin=dict(t=40, b=80, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.error("Could not load price gap data.")
        with st.expander("Error"):
            st.exception(exc)

# ── Tab 2: Penalty Exposure ───────────────────────────────────────────────────
with tab_penalty:
    st.subheader("Penalty Exposure")
    st.markdown(
        "Vendors that have a penalty clause **and** have late POs in the SCMS dataset."
    )
    try:
        pen_df = _penalty_exposure()
        if pen_df.empty:
            st.info("ℹ️ No penalty exposure detected.")
            if config.USE_MOCK_EXTRACTOR:
                st.markdown(_MOCK_NOTE)
        else:
            st.metric("Vendors with Exposure", len(pen_df))
            st.dataframe(pen_df, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.error("Could not load penalty exposure data.")
        with st.expander("Error"):
            st.exception(exc)

# ── Tab 3: Renewal Alerts ─────────────────────────────────────────────────────
with tab_renewal:
    st.subheader("Renewal Alerts")
    st.markdown(
        f"Contracts expiring within **{config.RENEWAL_ALERT_DAYS} days** "
        f"or already past their expiry date."
    )
    try:
        ren_df = _renewal_alerts()
        if ren_df.empty:
            st.success("✅ No renewal alerts — all contracts have future expiry dates.")
        else:
            # Summary metrics
            n_expired  = int((ren_df["status"] == "expired").sum())
            n_urgent   = int((ren_df["status"] == "urgent").sum())
            n_upcoming = int((ren_df["status"] == "upcoming").sum())

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Alerts",       len(ren_df))
            m2.metric("🔴 Expired",          n_expired)
            m3.metric("🟠 Urgent (≤30 days)", n_urgent)
            m4.metric("🟡 Upcoming",          n_upcoming)

            st.markdown("---")

            # Color-coded dataframe
            styled = ren_df.style.applymap(
                _style_status, subset=["status"]
            ).format({"days_until_expiry": "{:.0f}"}, na_rep="—")

            st.dataframe(styled, use_container_width=True, hide_index=True,
                         column_config={
                             "vendor_name":          st.column_config.TextColumn("Vendor"),
                             "contract_id":          st.column_config.TextColumn("Contract ID"),
                             "expiry_date":          st.column_config.TextColumn("Expiry Date"),
                             "days_until_expiry":    st.column_config.NumberColumn("Days Left"),
                             "renewal_type":         st.column_config.TextColumn("Renewal Type"),
                             "notice_days_required": st.column_config.NumberColumn("Notice Days"),
                             "status":               st.column_config.TextColumn("Status"),
                         })

            # Timeline chart
            chart_data = ren_df.copy()
            chart_data["expiry_date"] = pd.to_datetime(chart_data["expiry_date"])
            fig = px.scatter(
                chart_data.sort_values("days_until_expiry"),
                x="expiry_date",
                y="vendor_name",
                color="status",
                color_discrete_map={
                    "expired":  "#EF4444",
                    "urgent":   "#F97316",
                    "upcoming": "#EAB308",
                },
                size=[10] * len(chart_data),
                hover_data=["contract_id", "days_until_expiry", "renewal_type"],
                title="Contract Expiry Timeline",
            )
            fig.update_layout(height=420, margin=dict(t=40, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

    except Exception as exc:
        st.error("Could not load renewal alert data.")
        with st.expander("Error"):
            st.exception(exc)
