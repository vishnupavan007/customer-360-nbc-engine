import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Churn Risk Dashboard", page_icon="⚠️", layout="wide")
session = get_active_session()

st.title("Churn Risk Dashboard")
st.caption("AI-predicted churn risk analysis across customer segments")

with st.sidebar:
    st.header("Filters")
    segments = session.sql("SELECT DISTINCT CUSTOMER_SEGMENT FROM CUSTOMER_360.AI.DT_CHURN_RISK ORDER BY 1").to_pandas()
    selected = st.multiselect("Customer Segment", options=segments["CUSTOMER_SEGMENT"].tolist(), default=segments["CUSTOMER_SEGMENT"].tolist())
    risk_min = st.slider("Min Churn Risk Score", 0.0, 1.0, 0.0, 0.05)

seg_filter = "','".join(selected)

kpis = session.sql(f"""
    SELECT COUNT(*) AS TOTAL,
           SUM(CASE WHEN CHURN_RISK_SCORE >= 0.7 THEN 1 ELSE 0 END) AS HIGH_RISK,
           ROUND(AVG(CHURN_RISK_SCORE), 3) AS AVG_RISK,
           ROUND(AVG(MODEL_CONFIDENCE), 3) AS AVG_CONF
    FROM CUSTOMER_360.AI.DT_CHURN_RISK
    WHERE CUSTOMER_SEGMENT IN ('{seg_filter}')
      AND COALESCE(CHURN_RISK_SCORE, 0) >= {risk_min}
""").to_pandas()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Customers Analyzed", f"{kpis['TOTAL'].iloc[0]:,}")
k2.metric("High Risk (≥0.7)", f"{kpis['HIGH_RISK'].iloc[0]:,}")
k3.metric("Avg Churn Risk", f"{kpis['AVG_RISK'].iloc[0]:.3f}")
k4.metric("Avg Model Confidence", f"{kpis['AVG_CONF'].iloc[0]:.1%}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Risk Distribution")
    dist = session.sql(f"""
        SELECT CASE WHEN CHURN_RISK_SCORE >= 0.8 THEN '5-Critical'
                    WHEN CHURN_RISK_SCORE >= 0.6 THEN '4-High'
                    WHEN CHURN_RISK_SCORE >= 0.4 THEN '3-Medium'
                    WHEN CHURN_RISK_SCORE >= 0.2 THEN '2-Low'
                    ELSE '1-Minimal' END AS BUCKET,
               COUNT(*) AS CUSTOMERS
        FROM CUSTOMER_360.AI.DT_CHURN_RISK
        WHERE CUSTOMER_SEGMENT IN ('{seg_filter}') AND CHURN_RISK_SCORE IS NOT NULL
        GROUP BY 1 ORDER BY 1 DESC
    """).to_pandas()
    st.bar_chart(dist, x="BUCKET", y="CUSTOMERS", horizontal=True)

with right:
    st.subheader("Avg Risk by Segment")
    by_seg = session.sql(f"""
        SELECT CUSTOMER_SEGMENT, ROUND(AVG(CHURN_RISK_SCORE), 3) AS AVG_RISK
        FROM CUSTOMER_360.AI.DT_CHURN_RISK
        WHERE CUSTOMER_SEGMENT IN ('{seg_filter}') AND CHURN_RISK_SCORE IS NOT NULL
        GROUP BY 1 ORDER BY 2 DESC
    """).to_pandas()
    st.bar_chart(by_seg, x="CUSTOMER_SEGMENT", y="AVG_RISK")

st.divider()
st.subheader("High-Risk Customers")
detail = session.sql(f"""
    SELECT FULL_NAME, CUSTOMER_SEGMENT, ROUND(CHURN_RISK_SCORE, 3) AS CHURN_RISK,
           RETENTION_URGENCY, ROUND(MODEL_CONFIDENCE, 2) AS CONFIDENCE,
           COMPLAINT_COUNT, ESCALATION_COUNT, MAX_DAYS_PAST_DUE,
           ROUND(AVG_SENTIMENT_SCORE, 2) AS AVG_SENTIMENT, NEGATIVE_CALL_COUNT
    FROM CUSTOMER_360.AI.DT_CHURN_RISK
    WHERE CUSTOMER_SEGMENT IN ('{seg_filter}')
      AND COALESCE(CHURN_RISK_SCORE, 0) >= {risk_min}
    ORDER BY CHURN_RISK_SCORE DESC NULLS LAST LIMIT 50
""").to_pandas()
st.dataframe(detail, use_container_width=True, hide_index=True)
