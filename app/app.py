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

st.title("Customer 360 - Next Best Action Engine")
st.caption("Unified insurance & lending customer intelligence powered by Snowflake Cortex AI")


def safe_metric(query, column="CNT", default=0):
    try:
        df = session.sql(query).to_pandas()
        return df[column].iloc[0] if not df.empty else default
    except Exception:
        return default


HIGH_PRIORITY_Q = "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE PRIORITY = 'High'"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Customers", f"{safe_metric('SELECT COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED'):,}")
col2.metric("Active Customers", f"{safe_metric('SELECT COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED WHERE IS_ACTIVE = TRUE'):,}")
col3.metric("High Churn Risk", f"{safe_metric('SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE >= 0.7'):,}")
col4.metric("High Priority Actions", f"{safe_metric(HIGH_PRIORITY_Q):,}")

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
        st.bar_chart(churn_seg, x="CUSTOMER_SEGMENT", y="AVG_CHURN_RISK")
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
        st.bar_chart(sentiment, x="SENTIMENT_LABEL", y="CALL_COUNT")
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
    st.dataframe(top_actions, use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"Could not load action items: {e}")

st.sidebar.markdown("---")
st.sidebar.caption("Built with Snowflake Cortex AI + CoCo")
