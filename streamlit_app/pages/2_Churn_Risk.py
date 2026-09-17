import streamlit as st

st.set_page_config(page_title="Churn Risk Dashboard", page_icon="⚠️", layout="wide")
conn = st.connection("snowflake")

st.title("Churn Risk Dashboard")
st.caption("AI-predicted churn risk analysis across customer segments")

# Filters
with st.sidebar:
    st.header("Filters")
    segments = conn.query(
        "SELECT DISTINCT CUSTOMER_SEGMENT FROM CUSTOMER_360.AI.DT_CHURN_RISK ORDER BY 1"
    )
    selected_segments = st.multiselect(
        "Customer Segment",
        options=segments["CUSTOMER_SEGMENT"].tolist(),
        default=segments["CUSTOMER_SEGMENT"].tolist(),
    )
    risk_threshold = st.slider("Min Churn Risk Score", 0.0, 1.0, 0.0, 0.05)

seg_filter = "','".join(selected_segments)

# KPI row
k1, k2, k3, k4 = st.columns(4)

kpis = conn.query(f"""
    SELECT
        COUNT(*) AS TOTAL,
        SUM(CASE WHEN CHURN_RISK_SCORE >= 0.7 THEN 1 ELSE 0 END) AS HIGH_RISK,
        ROUND(AVG(CHURN_RISK_SCORE), 3) AS AVG_RISK,
        ROUND(AVG(MODEL_CONFIDENCE), 3) AS AVG_CONFIDENCE
    FROM CUSTOMER_360.AI.DT_CHURN_RISK
    WHERE CUSTOMER_SEGMENT IN ('{seg_filter}')
      AND COALESCE(CHURN_RISK_SCORE, 0) >= {risk_threshold}
""")

k1.metric("Customers Analyzed", f"{kpis['TOTAL'].iloc[0]:,}")
k2.metric("High Risk (>0.7)", f"{kpis['HIGH_RISK'].iloc[0]:,}")
k3.metric("Avg Churn Risk", f"{kpis['AVG_RISK'].iloc[0]:.3f}")
k4.metric("Avg Model Confidence", f"{kpis['AVG_CONFIDENCE'].iloc[0]:.1%}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Risk Distribution")
    dist = conn.query(f"""
        SELECT
            CASE
                WHEN CHURN_RISK_SCORE >= 0.8 THEN '5-Critical'
                WHEN CHURN_RISK_SCORE >= 0.6 THEN '4-High'
                WHEN CHURN_RISK_SCORE >= 0.4 THEN '3-Medium'
                WHEN CHURN_RISK_SCORE >= 0.2 THEN '2-Low'
                ELSE '1-Minimal'
            END AS RISK_BUCKET,
            COUNT(*) AS CUSTOMER_COUNT
        FROM CUSTOMER_360.AI.DT_CHURN_RISK
        WHERE CUSTOMER_SEGMENT IN ('{seg_filter}')
          AND CHURN_RISK_SCORE IS NOT NULL
        GROUP BY RISK_BUCKET
        ORDER BY RISK_BUCKET DESC
    """)
    st.bar_chart(dist, x="RISK_BUCKET", y="CUSTOMER_COUNT", horizontal=True)

with right:
    st.subheader("Avg Risk by Segment")
    by_seg = conn.query(f"""
        SELECT
            CUSTOMER_SEGMENT,
            ROUND(AVG(CHURN_RISK_SCORE), 3) AS AVG_RISK,
            COUNT(*) AS COUNT
        FROM CUSTOMER_360.AI.DT_CHURN_RISK
        WHERE CUSTOMER_SEGMENT IN ('{seg_filter}')
          AND CHURN_RISK_SCORE IS NOT NULL
        GROUP BY CUSTOMER_SEGMENT
        ORDER BY AVG_RISK DESC
    """)
    st.bar_chart(by_seg, x="CUSTOMER_SEGMENT", y="AVG_RISK")

st.divider()

st.subheader("Retention Urgency Breakdown")
urgency = conn.query(f"""
    SELECT
        RETENTION_URGENCY,
        CUSTOMER_SEGMENT,
        COUNT(*) AS CUSTOMER_COUNT
    FROM CUSTOMER_360.AI.DT_CHURN_RISK
    WHERE CUSTOMER_SEGMENT IN ('{seg_filter}')
      AND RETENTION_URGENCY IS NOT NULL
      AND COALESCE(CHURN_RISK_SCORE, 0) >= {risk_threshold}
    GROUP BY RETENTION_URGENCY, CUSTOMER_SEGMENT
    ORDER BY RETENTION_URGENCY, CUSTOMER_SEGMENT
""")
st.dataframe(urgency, use_container_width=True, hide_index=True)

st.divider()

st.subheader("High-Risk Customers Detail")
high_risk_detail = conn.query(f"""
    SELECT
        cr.FULL_NAME,
        cr.CUSTOMER_SEGMENT,
        ROUND(cr.CHURN_RISK_SCORE, 3) AS CHURN_RISK,
        cr.RETENTION_URGENCY,
        ROUND(cr.MODEL_CONFIDENCE, 2) AS CONFIDENCE,
        cr.COMPLAINT_COUNT,
        cr.ESCALATION_COUNT,
        cr.MAX_DAYS_PAST_DUE,
        ROUND(cr.AVG_SENTIMENT_SCORE, 2) AS AVG_SENTIMENT,
        cr.NEGATIVE_CALL_COUNT
    FROM CUSTOMER_360.AI.DT_CHURN_RISK cr
    WHERE cr.CUSTOMER_SEGMENT IN ('{seg_filter}')
      AND COALESCE(cr.CHURN_RISK_SCORE, 0) >= {risk_threshold}
    ORDER BY cr.CHURN_RISK_SCORE DESC
    LIMIT 50
""")
st.dataframe(high_risk_detail, use_container_width=True, hide_index=True)
