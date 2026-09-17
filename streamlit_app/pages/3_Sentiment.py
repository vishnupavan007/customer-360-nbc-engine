import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Sentiment Analysis", page_icon="💬", layout="wide")
session = get_active_session()

st.title("Call Sentiment Analysis")
st.caption("AI-powered sentiment insights from customer call transcripts")

kpis = session.sql("""
    SELECT COUNT(*) AS TOTAL,
           ROUND(AVG(SENTIMENT_SCORE), 3) AS AVG_SENT,
           SUM(CASE WHEN SENTIMENT_LABEL = 'Negative' THEN 1 ELSE 0 END) AS NEG,
           SUM(CASE WHEN SENTIMENT_LABEL = 'Positive' THEN 1 ELSE 0 END) AS POS
    FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
""").to_pandas()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Calls Analyzed", f"{kpis['TOTAL'].iloc[0]:,}")
k2.metric("Avg Sentiment Score", f"{kpis['AVG_SENT'].iloc[0]:.3f}")
k3.metric("Negative Calls", f"{kpis['NEG'].iloc[0]:,}")
k4.metric("Positive Calls", f"{kpis['POS'].iloc[0]:,}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Sentiment Distribution")
    dist = session.sql("""
        SELECT SENTIMENT_LABEL, COUNT(*) AS CALL_COUNT
        FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
        GROUP BY 1 ORDER BY CALL_COUNT DESC
    """).to_pandas()
    st.bar_chart(dist, x="SENTIMENT_LABEL", y="CALL_COUNT")

with right:
    st.subheader("Avg Sentiment by Call Reason")
    by_reason = session.sql("""
        SELECT CALL_REASON, ROUND(AVG(SENTIMENT_SCORE), 3) AS AVG_SENTIMENT, COUNT(*) AS CALLS
        FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
        GROUP BY CALL_REASON ORDER BY AVG_SENTIMENT ASC
    """).to_pandas()
    st.bar_chart(by_reason, x="CALL_REASON", y="AVG_SENTIMENT")

st.divider()

st.subheader("Sentiment by Agent")
by_agent = session.sql("""
    SELECT AGENT_NAME, COUNT(*) AS TOTAL_CALLS,
           ROUND(AVG(SENTIMENT_SCORE), 3) AS AVG_SENTIMENT,
           SUM(CASE WHEN SENTIMENT_LABEL = 'Negative' THEN 1 ELSE 0 END) AS NEGATIVE,
           SUM(CASE WHEN SENTIMENT_LABEL = 'Positive' THEN 1 ELSE 0 END) AS POSITIVE
    FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
    GROUP BY AGENT_NAME ORDER BY AVG_SENTIMENT ASC
""").to_pandas()
st.dataframe(by_agent, use_container_width=True, hide_index=True)

st.divider()

st.subheader("Negative Calls - Detail")
neg = session.sql("""
    SELECT s.CUSTOMER_ID, c.FULL_NAME, c.CUSTOMER_SEGMENT,
           s.CALL_REASON, s.AGENT_NAME,
           ROUND(s.SENTIMENT_SCORE, 3) AS SENTIMENT,
           s.CALL_SUMMARY, s.CALL_DATE
    FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT s
    JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c ON s.CUSTOMER_ID = c.CUSTOMER_ID
    WHERE s.SENTIMENT_LABEL = 'Negative'
    ORDER BY s.SENTIMENT_SCORE ASC LIMIT 20
""").to_pandas()
st.dataframe(neg, use_container_width=True, hide_index=True)

if not neg.empty:
    st.subheader("View Full Transcript")
    opts = {f"Customer {row['CUSTOMER_ID']} - {row['FULL_NAME']}": row['CUSTOMER_ID'] for _, row in neg.iterrows()}
    selected = st.selectbox("Select a negative call", options=list(opts.keys()))
    if selected:
        cid = opts[selected]
        transcript = session.sql(f"""
            SELECT TRANSCRIPT_TEXT FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
            WHERE CUSTOMER_ID = {cid} AND SENTIMENT_LABEL = 'Negative' LIMIT 1
        """).to_pandas()
        if not transcript.empty:
            st.text_area("Transcript", transcript["TRANSCRIPT_TEXT"].iloc[0], height=400)
