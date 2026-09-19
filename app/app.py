import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(
    page_title="Customer 360 | NBA Engine",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

# ── Global CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Badges ─────────────────────────────────────────────────────────────── */
.badge {
    display: inline-block; padding: 2px 10px;
    border-radius: 12px; font-size: 0.78rem; font-weight: 700;
    letter-spacing: 0.03em;
}
.badge-critical { background:#FFCDD2; color:#B71C1C; }
.badge-high     { background:#FFE0B2; color:#E65100; }
.badge-medium   { background:#FFF9C4; color:#F57F17; }
.badge-low      { background:#C8E6C9; color:#1B5E20; }
.badge-minimal  { background:#E8F5E9; color:#2E7D32; }

.badge-vip      { background:#F3E5F5; color:#6A1B9A; }
.badge-premium  { background:#E3F2FD; color:#0D47A1; }
.badge-standard { background:#E0F7FA; color:#006064; }
.badge-basic    { background:#EFEBE9; color:#4E342E; }

.badge-positive { background:#C8E6C9; color:#1B5E20; }
.badge-negative { background:#FFCDD2; color:#B71C1C; }
.badge-neutral  { background:#F5F5F5; color:#424242; }

/* ── KPI tiles ───────────────────────────────────────────────────────────── */
.kpi-tile {
    background: white; border-radius: 10px; padding: 16px 20px;
    border-left: 5px solid #29B5E8;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.kpi-tile.danger  { border-left-color: #D32F2F; }
.kpi-tile.warning { border-left-color: #F57C00; }
.kpi-tile.success { border-left-color: #388E3C; }
.kpi-tile.info    { border-left-color: #29B5E8; }
.kpi-label { font-size: 0.78rem; font-weight: 600; color: #636efa; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
.kpi-value { font-size: 1.9rem; font-weight: 800; color: #262730; line-height: 1.1; }
.kpi-tile.danger  .kpi-value { color: #C62828; }
.kpi-tile.warning .kpi-value { color: #E65100; }
.kpi-tile.success .kpi-value { color: #2E7D32; }

/* ── Section header ─────────────────────────────────────────────────────── */
.section-header {
    background: linear-gradient(90deg, #29B5E8 0%, #11567F 100%);
    color: white; padding: 10px 18px; border-radius: 8px;
    font-size: 1.05rem; font-weight: 700; margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)


def kpi_tile(label, value, variant="info"):
    st.markdown(
        f'<div class="kpi-tile {variant}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def badge(text, kind):
    return f'<span class="badge badge-{kind.lower()}">{text}</span>'


# ── Header ──────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-header">🏦 Customer 360 — Next Best Action Engine</div>',
    unsafe_allow_html=True,
)
st.caption("Unified insurance & lending customer intelligence powered by Snowflake Cortex AI")


def safe_metric(query, column="CNT", default=0):
    try:
        df = session.sql(query).to_pandas()
        return df[column].iloc[0] if not df.empty else default
    except Exception:
        return default


HIGH_PRIORITY_Q = "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE PRIORITY = 'High'"

col1, col2, col3, col4 = st.columns(4)
with col1:
    kpi_tile("Total Customers", f"{safe_metric('SELECT COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED'):,}", "info")
with col2:
    kpi_tile("Active Customers", f"{safe_metric('SELECT COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED WHERE IS_ACTIVE = TRUE'):,}", "success")
with col3:
    kpi_tile("High Churn Risk", f"{safe_metric('SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE >= 0.7'):,}", "danger")
with col4:
    kpi_tile("High Priority Actions", f"{safe_metric(HIGH_PRIORITY_Q):,}", "warning")

st.markdown("<br>", unsafe_allow_html=True)
st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Churn Risk by Segment")
    try:
        churn_seg = session.sql("""
            SELECT c.CUSTOMER_SEGMENT,
                   ROUND(AVG(cr.CHURN_RISK_SCORE), 3) AS AVG_CHURN_RISK,
                   COUNT(*) AS CUSTOMER_COUNT
            FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
            JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID = cr.CUSTOMER_ID
            WHERE cr.CHURN_RISK_SCORE IS NOT NULL
            GROUP BY c.CUSTOMER_SEGMENT
            ORDER BY AVG_CHURN_RISK DESC
        """).to_pandas()
        st.bar_chart(churn_seg, x="CUSTOMER_SEGMENT", y="AVG_CHURN_RISK", color="#29B5E8")
    except Exception as e:
        st.error(f"Could not load churn chart: {e}")

with right:
    st.subheader("Sentiment Distribution")
    try:
        sentiment = session.sql("""
            SELECT SENTIMENT_LABEL, COUNT(*) AS CALL_COUNT
            FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
            GROUP BY SENTIMENT_LABEL ORDER BY CALL_COUNT DESC
        """).to_pandas()
        colors = {"Positive": "#388E3C", "Neutral": "#1976D2", "Negative": "#D32F2F"}
        sentiment["COLOR"] = sentiment["SENTIMENT_LABEL"].map(colors).fillna("#29B5E8")
        st.bar_chart(sentiment, x="SENTIMENT_LABEL", y="CALL_COUNT", color="COLOR")
    except Exception as e:
        st.error(f"Could not load sentiment chart: {e}")

st.divider()
st.subheader("Top Action Items")
try:
    top_actions = session.sql("""
        SELECT nba.FULL_NAME, nba.CUSTOMER_SEGMENT,
               ROUND(nba.CHURN_RISK_SCORE, 2) AS CHURN_RISK,
               nba.ACTION_TYPE, nba.ACTION_DESCRIPTION,
               nba.PRIORITY, nba.RECOMMENDED_CHANNEL
        FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba
        WHERE nba.PRIORITY = 'High' AND nba.ACTION_TYPE IS NOT NULL
        ORDER BY nba.CHURN_RISK_SCORE DESC
        LIMIT 15
    """).to_pandas()

    def color_risk(v):
        if isinstance(v, float):
            if v >= 0.8: return "background-color:#FFCDD2;color:#B71C1C;font-weight:bold"
            if v >= 0.6: return "background-color:#FFE0B2;color:#E65100"
            if v >= 0.4: return "background-color:#FFF9C4;color:#F57F17"
            return "background-color:#C8E6C9;color:#1B5E20"
        return ""

    styled = top_actions.style.map(color_risk, subset=["CHURN_RISK"])
    st.dataframe(styled, use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"Could not load action items: {e}")

st.sidebar.markdown("---")
st.sidebar.caption("Built with Snowflake Cortex AI + CoCo")
