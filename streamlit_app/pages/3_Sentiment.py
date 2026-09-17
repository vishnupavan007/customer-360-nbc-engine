import streamlit as st

st.set_page_config(page_title="Sentiment Analysis", page_icon="💬", layout="wide")
conn = st.connection("snowflake")

st.title("Call Sentiment Analysis")
st.caption("AI-powered sentiment insights from customer call transcripts")

# KPIs
k1, k2, k3, k4 = st.columns(4)

kpis = conn.query("""
    SELECT
        COUNT(*) AS TOTAL_CALLS,
        ROUND(AVG(SENTIMENT_SCORE), 3) AS AVG_SENTIMENT,
        SUM(CASE WHEN SENTIMENT_LABEL = 'Negative' THEN 1 ELSE 0 END) AS NEGATIVE_CALLS,
        SUM(CASE WHEN SENTIMENT_LABEL = 'Positive' THEN 1 ELSE 0 END) AS POSITIVE_CALLS
    FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
""")

k1.metric("Total Calls Analyzed", f"{kpis['TOTAL_CALLS'].iloc[0]:,}")
k2.metric("Avg Sentiment Score", f"{kpis['AVG_SENTIMENT'].iloc[0]:.3f}")
k3.metric("Negative Calls", f"{kpis['NEGATIVE_CALLS'].iloc[0]:,}")
k4.metric("Positive Calls", f"{kpis['POSITIVE_CALLS'].iloc[0]:,}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Sentiment Distribution")
    dist = conn.query("""
        SELECT SENTIMENT_LABEL, COUNT(*) AS CALL_COUNT
        FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
        GROUP BY SENTIMENT_LABEL
        ORDER BY CALL_COUNT DESC
    """)
    st.bar_chart(dist, x="SENTIMENT_LABEL", y="CALL_COUNT")

with right:
    st.subheader("Avg Sentiment by Call Reason")
    by_reason = conn.query("""
        SELECT CALL_REASON, ROUND(AVG(SENTIMENT_SCORE), 3) AS AVG_SENTIMENT, COUNT(*) AS CALLS
        FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
        GROUP BY CALL_REASON
        ORDER BY AVG_SENTIMENT ASC
    """)
    st.bar_chart(by_reason, x="CALL_REASON", y="AVG_SENTIMENT")

st.divider()

st.subheader("Sentiment by Agent")
by_agent = conn.query("""
    SELECT
        AGENT_NAME,
        COUNT(*) AS TOTAL_CALLS,
        ROUND(AVG(SENTIMENT_SCORE), 3) AS AVG_SENTIMENT,
        SUM(CASE WHEN SENTIMENT_LABEL = 'Negative' THEN 1 ELSE 0 END) AS NEGATIVE,
        SUM(CASE WHEN SENTIMENT_LABEL = 'Positive' THEN 1 ELSE 0 END) AS POSITIVE
    FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
    GROUP BY AGENT_NAME
    ORDER BY AVG_SENTIMENT ASC
""")
st.dataframe(by_agent, use_container_width=True, hide_index=True)

st.divider()

# Drill-down: negative calls
st.subheader("Negative Sentiment Calls - Detail")
negative_calls = conn.query("""
    SELECT
        s.CUSTOMER_ID,
        c.FULL_NAME,
        c.CUSTOMER_SEGMENT,
        s.CALL_REASON,
        s.AGENT_NAME,
        ROUND(s.SENTIMENT_SCORE, 3) AS SENTIMENT,
        s.CALL_SUMMARY,
        s.CALL_DATE
    FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT s
    JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c ON s.CUSTOMER_ID = c.CUSTOMER_ID
    WHERE s.SENTIMENT_LABEL = 'Negative'
    ORDER BY s.SENTIMENT_SCORE ASC
    LIMIT 20
""")
st.dataframe(negative_calls, use_container_width=True, hide_index=True)

# Expandable transcript viewer
if not negative_calls.empty:
    st.subheader("View Full Transcript")
    selected_cust = st.selectbox(
        "Select a negative call to view",
        options=negative_calls["CUSTOMER_ID"].tolist(),
        format_func=lambda x: f"Customer {x} - {negative_calls[negative_calls['CUSTOMER_ID']==x]['FULL_NAME'].iloc[0]}",
    )
    if selected_cust:
        transcript = conn.query(f"""
            SELECT TRANSCRIPT_TEXT
            FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
            WHERE CUSTOMER_ID = {selected_cust}
              AND SENTIMENT_LABEL = 'Negative'
            LIMIT 1
        """)
        if not transcript.empty:
            st.text_area("Transcript", transcript["TRANSCRIPT_TEXT"].iloc[0], height=400)
