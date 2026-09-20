import streamlit as st
from snowflake.snowpark.context import get_active_session
from utils import apply_theme, theme_sidebar, render_df

st.set_page_config(page_title="Customer 360", page_icon="🏠", layout="wide")
apply_theme()

session = get_active_session()

with st.sidebar:
    theme_sidebar()

def run_query(query):
    return session.sql(query).to_pandas()

def safe_metric(query, column="CNT", default=0):
    try:
        df = run_query(query)
        return df[column].iloc[0] if not df.empty else default
    except Exception:
        return default

st.title("Customer 360 — Next Best Action Engine")
st.caption("Unified insurance and lending customer intelligence powered by Snowflake Cortex AI")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Customers",
              f"{safe_metric('SELECT COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED'):,}")
with col2:
    st.metric("Active Customers",
              f"{safe_metric('SELECT COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED WHERE IS_ACTIVE = TRUE'):,}")
with col3:
    st.metric("High Churn Risk",
              f"{safe_metric('SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE >= 0.7'):,}")
with col4:
    q = "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE PRIORITY = 'High'"
    st.metric("High Priority Actions", f"{safe_metric(q):,}")

st.markdown("---")

left, right = st.columns(2)

with left:
    st.subheader("Churn Risk by Segment")
    try:
        churn_seg = run_query("""
            SELECT c.CUSTOMER_SEGMENT,
                   ROUND(AVG(cr.CHURN_RISK_SCORE), 3) AS AVG_CHURN_RISK
            FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
            JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID = cr.CUSTOMER_ID
            WHERE cr.CHURN_RISK_SCORE IS NOT NULL
            GROUP BY c.CUSTOMER_SEGMENT
            ORDER BY AVG_CHURN_RISK DESC
        """)
        st.bar_chart(churn_seg.set_index("CUSTOMER_SEGMENT"))
    except Exception as e:
        st.error(str(e))

with right:
    st.subheader("Sentiment Distribution")
    try:
        sentiment = run_query("""
            SELECT SENTIMENT_LABEL, COUNT(*) AS CALL_COUNT
            FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
            GROUP BY SENTIMENT_LABEL ORDER BY CALL_COUNT DESC
        """)
        st.bar_chart(sentiment.set_index("SENTIMENT_LABEL"))
    except Exception as e:
        st.error(str(e))

st.markdown("---")
st.subheader("Top Action Items")
try:
    top_actions = run_query("""
        SELECT nba.FULL_NAME, nba.CUSTOMER_SEGMENT,
               ROUND(nba.CHURN_RISK_SCORE, 2) AS CHURN_RISK,
               nba.ACTION_TYPE, nba.ACTION_DESCRIPTION,
               nba.PRIORITY, nba.RECOMMENDED_CHANNEL
        FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba
        WHERE nba.PRIORITY = 'High' AND nba.ACTION_TYPE IS NOT NULL
        ORDER BY nba.CHURN_RISK_SCORE DESC
        LIMIT 15
    """)
    render_df(top_actions)
except Exception as e:
    st.error(str(e))
