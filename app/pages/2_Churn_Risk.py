import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Churn Risk Dashboard", page_icon="⚠️", layout="wide")

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

st.markdown("""
<style>
.badge { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:700; }
.badge-critical { background:#FFCDD2; color:#B71C1C; }
.badge-high     { background:#FFE0B2; color:#E65100; }
.badge-medium   { background:#FFF9C4; color:#F57F17; }
.badge-low      { background:#C8E6C9; color:#1B5E20; }
.badge-minimal  { background:#E8F5E9; color:#2E7D32; }
</style>
""", unsafe_allow_html=True)

st.title("Churn Risk Dashboard")
st.caption("AI-predicted churn risk analysis across customer segments")

try:
    seg_df = session.sql("SELECT DISTINCT CUSTOMER_SEGMENT FROM CUSTOMER_360.AI.DT_CHURN_RISK ORDER BY 1").to_pandas()
    all_segments = seg_df["CUSTOMER_SEGMENT"].tolist()
except Exception as e:
    st.error(f"Could not load segments: {e}")
    st.stop()

with st.sidebar:
    st.header("Filters")
    selected = st.multiselect("Customer Segment", options=all_segments, default=all_segments)
    risk_min = st.slider("Min Churn Risk Score", 0.0, 1.0, 0.0, 0.05)

if not selected:
    st.warning("Please select at least one customer segment.")
    st.stop()

valid_segments = set(all_segments)
safe_selected = [s for s in selected if s in valid_segments]
if not safe_selected:
    st.warning("No valid segments selected.")
    st.stop()

seg_placeholders = ", ".join([f"'{s}'" for s in safe_selected])
risk_min_val = float(risk_min)


def safe_sql(query, error_label="data"):
    try:
        return session.sql(query).to_pandas()
    except Exception as e:
        st.error(f"Could not load {error_label}: {e}")
        return None


kpis = safe_sql(f"""
    SELECT COUNT(*) AS TOTAL,
           SUM(CASE WHEN CHURN_RISK_SCORE >= 0.7 THEN 1 ELSE 0 END) AS HIGH_RISK,
           ROUND(AVG(CHURN_RISK_SCORE), 3) AS AVG_RISK,
           ROUND(AVG(MODEL_CONFIDENCE), 3) AS AVG_CONF
    FROM CUSTOMER_360.AI.DT_CHURN_RISK
    WHERE CUSTOMER_SEGMENT IN ({seg_placeholders})
      AND COALESCE(CHURN_RISK_SCORE, 0) >= {risk_min_val}
""", "KPIs")

if kpis is not None:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Customers Analyzed", f"{kpis['TOTAL'].iloc[0]:,}")
    high = int(kpis['HIGH_RISK'].iloc[0])
    total = int(kpis['TOTAL'].iloc[0])
    k2.metric("High Risk (≥0.7)", f"{high:,}", delta=f"{high/total:.0%} of total" if total else None, delta_color="inverse")
    k3.metric("Avg Churn Risk", f"{kpis['AVG_RISK'].iloc[0]:.3f}")
    k4.metric("Avg Model Confidence", f"{kpis['AVG_CONF'].iloc[0]:.1%}")

st.markdown("---")
left, right = st.columns(2)

with left:
    st.subheader("Risk Distribution")
    dist = safe_sql(f"""
        SELECT CASE WHEN CHURN_RISK_SCORE >= 0.8 THEN '5-Critical'
                    WHEN CHURN_RISK_SCORE >= 0.6 THEN '4-High'
                    WHEN CHURN_RISK_SCORE >= 0.4 THEN '3-Medium'
                    WHEN CHURN_RISK_SCORE >= 0.2 THEN '2-Low'
                    ELSE '1-Minimal' END AS BUCKET,
               COUNT(*) AS CUSTOMERS
        FROM CUSTOMER_360.AI.DT_CHURN_RISK
        WHERE CUSTOMER_SEGMENT IN ({seg_placeholders}) AND CHURN_RISK_SCORE IS NOT NULL
        GROUP BY 1 ORDER BY 1 DESC
    """, "risk distribution")
    if dist is not None:
        bucket_colors = {
            "5-Critical": "#B71C1C", "4-High": "#E65100",
            "3-Medium": "#F9A825", "2-Low": "#43A047", "1-Minimal": "#1B5E20",
        }
        st.bar_chart(dist.set_index("BUCKET")["CUSTOMERS"])

with right:
    st.subheader("Avg Risk by Segment")
    by_seg = safe_sql(f"""
        SELECT CUSTOMER_SEGMENT, ROUND(AVG(CHURN_RISK_SCORE), 3) AS AVG_RISK
        FROM CUSTOMER_360.AI.DT_CHURN_RISK
        WHERE CUSTOMER_SEGMENT IN ({seg_placeholders}) AND CHURN_RISK_SCORE IS NOT NULL
        GROUP BY 1 ORDER BY 2 DESC
    """, "segment risk")
    if by_seg is not None:
        st.bar_chart(by_seg.set_index("CUSTOMER_SEGMENT")["AVG_RISK"])

st.markdown("---")
st.subheader("High-Risk Customers")

detail = safe_sql(f"""
    SELECT FULL_NAME, CUSTOMER_SEGMENT, ROUND(CHURN_RISK_SCORE, 3) AS CHURN_RISK,
           RETENTION_URGENCY, ROUND(MODEL_CONFIDENCE, 2) AS CONFIDENCE,
           COMPLAINT_COUNT, ESCALATION_COUNT, MAX_DAYS_PAST_DUE,
           ROUND(AVG_SENTIMENT_SCORE, 2) AS AVG_SENTIMENT, NEGATIVE_CALL_COUNT
    FROM CUSTOMER_360.AI.DT_CHURN_RISK
    WHERE CUSTOMER_SEGMENT IN ({seg_placeholders})
      AND COALESCE(CHURN_RISK_SCORE, 0) >= {risk_min_val}
    ORDER BY CHURN_RISK_SCORE DESC NULLS LAST LIMIT 50
""", "customer detail")

if detail is not None:
    def style_risk(v):
        if not isinstance(v, float): return ""
        if v >= 0.8: return "background-color:#FFCDD2;color:#B71C1C;font-weight:bold"
        if v >= 0.6: return "background-color:#FFE0B2;color:#E65100"
        if v >= 0.4: return "background-color:#FFF9C4;color:#F57F17"
        return "background-color:#C8E6C9;color:#1B5E20"

    def style_urgency(v):
        return {
            "Critical": "background-color:#FFCDD2;color:#B71C1C;font-weight:bold",
            "High":     "background-color:#FFE0B2;color:#E65100",
            "Medium":   "background-color:#FFF9C4;color:#F57F17",
            "Low":      "background-color:#C8E6C9;color:#1B5E20",
        }.get(str(v), "")

    styled = (
        detail.style
        .map(style_risk, subset=["CHURN_RISK"])
        .map(style_urgency, subset=["RETENTION_URGENCY"])
    )
    st.dataframe(styled)
