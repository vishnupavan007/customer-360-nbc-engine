import streamlit as st

st.set_page_config(
    page_title="Customer 360 | NBC Engine",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

conn = st.connection("snowflake")

st.title("Customer 360 - Next Best Action Engine")
st.caption("Unified insurance & lending customer intelligence powered by Snowflake Cortex AI")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total = conn.query("SELECT COUNT(*) AS cnt FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED")
    st.metric("Total Customers", f"{total['CNT'].iloc[0]:,}")

with col2:
    active = conn.query(
        "SELECT COUNT(*) AS cnt FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED WHERE IS_ACTIVE = TRUE"
    )
    st.metric("Active Customers", f"{active['CNT'].iloc[0]:,}")

with col3:
    high_risk = conn.query(
        "SELECT COUNT(*) AS cnt FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE >= 0.7"
    )
    st.metric("High Churn Risk", f"{high_risk['CNT'].iloc[0]:,}")

with col4:
    pending_actions = conn.query(
        "SELECT COUNT(*) AS cnt FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE PRIORITY = 'High'"
    )
    st.metric("High Priority Actions", f"{pending_actions['CNT'].iloc[0]:,}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Churn Risk by Segment")
    churn_seg = conn.query("""
        SELECT
            c.CUSTOMER_SEGMENT,
            ROUND(AVG(cr.CHURN_RISK_SCORE), 3) AS AVG_CHURN_RISK,
            COUNT(*) AS CUSTOMER_COUNT
        FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
        JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID = cr.CUSTOMER_ID
        WHERE cr.CHURN_RISK_SCORE IS NOT NULL
        GROUP BY c.CUSTOMER_SEGMENT
        ORDER BY AVG_CHURN_RISK DESC
    """)
    st.bar_chart(churn_seg, x="CUSTOMER_SEGMENT", y="AVG_CHURN_RISK")

with right:
    st.subheader("Sentiment Distribution")
    sentiment = conn.query("""
        SELECT SENTIMENT_LABEL, COUNT(*) AS CALL_COUNT
        FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
        GROUP BY SENTIMENT_LABEL
        ORDER BY CALL_COUNT DESC
    """)
    st.bar_chart(sentiment, x="SENTIMENT_LABEL", y="CALL_COUNT")

st.divider()

st.subheader("Top Action Items")
top_actions = conn.query("""
    SELECT
        nba.FULL_NAME,
        nba.CUSTOMER_SEGMENT,
        ROUND(nba.CHURN_RISK_SCORE, 2) AS CHURN_RISK,
        nba.ACTION_TYPE,
        nba.ACTION_DESCRIPTION,
        nba.PRIORITY,
        nba.RECOMMENDED_CHANNEL
    FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba
    WHERE nba.PRIORITY = 'High' AND nba.ACTION_TYPE IS NOT NULL
    ORDER BY nba.CHURN_RISK_SCORE DESC
    LIMIT 15
""")
st.dataframe(top_actions, use_container_width=True, hide_index=True)

st.sidebar.markdown("---")
st.sidebar.caption("Built with Snowflake Cortex AI + CoCo")
