import streamlit as st
from snowflake.snowpark.context import get_active_session
from utils import apply_theme, theme_sidebar, render_df

st.set_page_config(page_title="Sentiment Analysis", page_icon="💬", layout="wide")
apply_theme()

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

with st.sidebar:
    theme_sidebar()

st.title("Call Sentiment Analysis")
st.caption("AI-powered sentiment insights from customer call transcripts")

col_date1, col_date2 = st.columns(2)
with col_date1:
    date_from = st.date_input("From", value=None, key="sent_from")
with col_date2:
    date_to = st.date_input("To", value=None, key="sent_to")

date_filter = ""
if date_from:
    date_filter += f" AND CALL_DATE >= '{date_from}'"
if date_to:
    date_filter += f" AND CALL_DATE <= '{date_to}'"


@st.cache_data(ttl=300, show_spinner=False)
def safe_sql(query, error_label="data"):
    try:
        return session.sql(query).to_pandas()
    except Exception as e:
        st.error(f"Could not load {error_label}: {e}")
        return None


kpis = safe_sql(f"""
    SELECT COUNT(*) AS TOTAL,
           ROUND(AVG(SENTIMENT_SCORE), 3) AS AVG_SENT,
           SUM(CASE WHEN SENTIMENT_LABEL = 'Negative' THEN 1 ELSE 0 END) AS NEG,
           SUM(CASE WHEN SENTIMENT_LABEL = 'Positive' THEN 1 ELSE 0 END) AS POS
    FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
    WHERE 1=1{date_filter}
""", "KPIs")

if kpis is not None:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Calls Analyzed", f"{kpis['TOTAL'].iloc[0]:,}")
    k2.metric("Avg Sentiment Score", f"{kpis['AVG_SENT'].iloc[0]:.3f}")
    k3.metric("Negative Calls", f"{kpis['NEG'].iloc[0]:,}")
    k4.metric("Positive Calls", f"{kpis['POS'].iloc[0]:,}")

st.markdown("---")

left, right = st.columns(2)

with left:
    st.subheader("Sentiment Distribution")
    dist = safe_sql(f"""
        SELECT SENTIMENT_LABEL, COUNT(*) AS CALL_COUNT
        FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
        WHERE 1=1{date_filter}
        GROUP BY 1 ORDER BY CALL_COUNT DESC
    """, "sentiment distribution")
    if dist is not None:
        st.bar_chart(dist, x="SENTIMENT_LABEL", y="CALL_COUNT")

with right:
    st.subheader("Avg Sentiment by Call Reason")
    by_reason = safe_sql(f"""
        SELECT CALL_REASON, ROUND(AVG(SENTIMENT_SCORE), 3) AS AVG_SENTIMENT, COUNT(*) AS CALLS
        FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
        WHERE 1=1{date_filter}
        GROUP BY CALL_REASON ORDER BY AVG_SENTIMENT ASC
    """, "sentiment by reason")
    if by_reason is not None:
        st.bar_chart(by_reason, x="CALL_REASON", y="AVG_SENTIMENT")

st.markdown("---")

st.subheader("Sentiment by Agent")
by_agent = safe_sql(f"""
    SELECT AGENT_NAME, COUNT(*) AS TOTAL_CALLS,
           ROUND(AVG(SENTIMENT_SCORE), 3) AS AVG_SENTIMENT,
           SUM(CASE WHEN SENTIMENT_LABEL = 'Negative' THEN 1 ELSE 0 END) AS NEGATIVE,
           SUM(CASE WHEN SENTIMENT_LABEL = 'Positive' THEN 1 ELSE 0 END) AS POSITIVE
    FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
    WHERE 1=1{date_filter}
    GROUP BY AGENT_NAME ORDER BY AVG_SENTIMENT ASC
""", "agent sentiment")
if by_agent is not None:
    render_df(by_agent)

st.markdown("---")
st.subheader("Sentiment Trend Over Time")
try:
    trend = safe_sql(f"""
        SELECT DATE_TRUNC('WEEK', CALL_DATE) AS WEEK,
               ROUND(AVG(SENTIMENT_SCORE), 3) AS AVG_SENTIMENT,
               COUNT(*) AS CALL_COUNT
        FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
        WHERE 1=1{date_filter}
        GROUP BY DATE_TRUNC('WEEK', CALL_DATE)
        ORDER BY WEEK
    """, "sentiment trend")
    if trend is not None and not trend.empty:
        st.line_chart(trend.set_index("WEEK")["AVG_SENTIMENT"])
        st.caption(f"Weekly average sentiment across {trend['CALL_COUNT'].sum()} calls")
except Exception as e:
    st.error(str(e))

st.markdown("---")

st.subheader("Negative Calls - Detail")
neg = safe_sql(f"""
    SELECT s.CUSTOMER_ID, c.FULL_NAME, c.CUSTOMER_SEGMENT,
           s.CALL_REASON, s.AGENT_NAME,
           ROUND(s.SENTIMENT_SCORE, 3) AS SENTIMENT,
           s.CALL_SUMMARY, s.CALL_DATE
    FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT s
    JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c ON s.CUSTOMER_ID = c.CUSTOMER_ID
    WHERE s.SENTIMENT_LABEL = 'Negative'{date_filter}
    ORDER BY s.SENTIMENT_SCORE ASC LIMIT 20
""", "negative calls")

if neg is not None and not neg.empty:
    render_df(neg)

    st.subheader("View Full Transcript")
    opts = {f"Customer {row['CUSTOMER_ID']} - {row['FULL_NAME']}": int(row['CUSTOMER_ID']) for _, row in neg.iterrows()}
    selected = st.selectbox("Select a negative call", options=list(opts.keys()))
    if selected:
        cid = opts[selected]
        # Read transcript from CLEAN table (not the AI table -- more efficient)
        transcript = safe_sql(
            f"SELECT TRANSCRIPT_TEXT FROM CUSTOMER_360.CLEAN.DT_CALL_TRANSCRIPTS"
            f" WHERE CUSTOMER_ID = {cid} LIMIT 1",
            "transcript"
        )
        if transcript is not None and not transcript.empty:
            st.text_area("Transcript", transcript["TRANSCRIPT_TEXT"].iloc[0], height=400)
