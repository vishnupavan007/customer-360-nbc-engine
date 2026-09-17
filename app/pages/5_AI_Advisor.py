import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="AI Advisor", page_icon="🤖", layout="wide")

st.title("Customer 360 AI Advisor")
st.caption("Ask natural-language questions about customers, churn risk, sentiment, and next best actions")

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "dataframes" not in st.session_state:
    st.session_state.dataframes = {}  # message_index -> dataframe

with st.sidebar:
    st.header("Example Questions")
    examples = [
        "How many high-risk churn customers are in the Premium segment?",
        "What is the average sentiment score by customer segment?",
        "Show me top 10 customers by churn risk with their next best action",
        "What are the most common actions for customers with negative sentiment?",
        "How many customers have more than 2 complaints?",
        "What is the churn risk distribution across segments?",
        "Which customers have open claims and high churn risk?",
    ]
    for ex in examples:
        if st.button(ex, key=ex, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": ex})
            st.rerun()

    st.divider()
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.dataframes = {}
        st.rerun()

MAX_QUESTION_LENGTH = 500


def call_cortex_llm(question: str):
    """Call CORTEX.COMPLETE. Returns (text_response, None, is_live_data=False)."""
    sanitized = "".join(c for c in question if c.isalnum() or c in " .,?-_'")[:MAX_QUESTION_LENGTH]
    try:
        safe_q = sanitized.replace("'", "''")
        result = session.sql(
            "SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b',"
            " 'You are a Customer 360 AI Advisor for insurance and lending. "
            "Answer questions about: segments (Basic/Standard/Premium/VIP), "
            "policies (Auto/Home/Life/Health), loans (Mortgage/Auto/Personal/Business), "
            "churn risk (0-1 score). Be specific. Question: " + safe_q + "') AS RESPONSE"
        ).collect()
        return (result[0]["RESPONSE"] if result else "No response received.", None, False)
    except Exception as e:
        return (f"Unable to answer: {str(e)}", None, False)


def answer_with_data(question: str):
    """Route to SQL queries or fall back to LLM. Returns (text, dataframe_or_None, is_live_data)."""
    q = question.lower()

    if "top" in q and "churn" in q:
        try:
            df = session.sql("""
                SELECT cr.FULL_NAME, cr.CUSTOMER_SEGMENT,
                       ROUND(cr.CHURN_RISK_SCORE, 3) AS CHURN_RISK,
                       cr.RETENTION_URGENCY, nba.ACTION_TYPE, nba.PRIORITY
                FROM CUSTOMER_360.AI.DT_CHURN_RISK cr
                LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba ON cr.CUSTOMER_ID = nba.CUSTOMER_ID
                WHERE cr.CHURN_RISK_SCORE IS NOT NULL
                ORDER BY cr.CHURN_RISK_SCORE DESC LIMIT 10
            """).to_pandas()
            return ("Top 10 customers by churn risk:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "sentiment" in q and "segment" in q:
        try:
            df = session.sql("""
                SELECT c.CUSTOMER_SEGMENT,
                       ROUND(AVG(s.SENTIMENT_SCORE), 3) AS AVG_SENTIMENT,
                       COUNT(*) AS CALL_COUNT
                FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
                JOIN CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT s ON c.CUSTOMER_ID = s.CUSTOMER_ID
                GROUP BY c.CUSTOMER_SEGMENT ORDER BY AVG_SENTIMENT
            """).to_pandas()
            return ("Average sentiment by segment:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "distribution" in q and "churn" in q:
        try:
            df = session.sql("""
                SELECT
                    CASE WHEN CHURN_RISK_SCORE >= 0.8 THEN 'Critical (0.8-1.0)'
                         WHEN CHURN_RISK_SCORE >= 0.6 THEN 'High (0.6-0.8)'
                         WHEN CHURN_RISK_SCORE >= 0.4 THEN 'Medium (0.4-0.6)'
                         WHEN CHURN_RISK_SCORE >= 0.2 THEN 'Low (0.2-0.4)'
                         ELSE 'Minimal (0-0.2)'
                    END AS RISK_BUCKET, COUNT(*) AS CUSTOMERS
                FROM CUSTOMER_360.AI.DT_CHURN_RISK
                WHERE CHURN_RISK_SCORE IS NOT NULL
                GROUP BY 1 ORDER BY 1
            """).to_pandas()
            return ("Churn risk distribution:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "premium" in q and ("high" in q or "risk" in q):
        try:
            df = session.sql("""
                SELECT COUNT(*) AS HIGH_RISK_PREMIUM
                FROM CUSTOMER_360.AI.DT_CHURN_RISK
                WHERE CHURN_RISK_SCORE >= 0.7 AND CUSTOMER_SEGMENT = 'Premium'
            """).to_pandas()
            count = df["HIGH_RISK_PREMIUM"].iloc[0]
            return (f"There are **{count}** high-risk churn customers (score >= 0.7) in the Premium segment.", None, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "action" in q and ("negative" in q or "sentiment" in q):
        try:
            df = session.sql("""
                SELECT nba.ACTION_TYPE, COUNT(*) AS ACTION_COUNT
                FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba
                WHERE nba.LATEST_SENTIMENT_LABEL = 'Negative' AND nba.ACTION_TYPE IS NOT NULL
                GROUP BY nba.ACTION_TYPE ORDER BY ACTION_COUNT DESC
            """).to_pandas()
            return ("Most common actions for customers with negative sentiment:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "complaint" in q:
        try:
            df = session.sql("""
                SELECT c.FULL_NAME, c.CUSTOMER_SEGMENT,
                       c.COMPLAINT_COUNT, c.ESCALATION_COUNT,
                       ROUND(cr.CHURN_RISK_SCORE, 3) AS CHURN_RISK,
                       cr.RETENTION_URGENCY,
                       nba.ACTION_TYPE, nba.PRIORITY,
                       nba.ACTION_DESCRIPTION
                FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
                LEFT JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID = cr.CUSTOMER_ID
                LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba ON c.CUSTOMER_ID = nba.CUSTOMER_ID
                WHERE c.COMPLAINT_COUNT > 2
                ORDER BY c.COMPLAINT_COUNT DESC, cr.CHURN_RISK_SCORE DESC
            """).to_pandas()
            count = len(df)
            return (f"**{count}** customers have more than 2 complaints. Here are their details and recommended actions:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "claim" in q and ("churn" in q or "risk" in q):
        try:
            df = session.sql("""
                SELECT cr.FULL_NAME, cr.CUSTOMER_SEGMENT,
                       ROUND(cr.CHURN_RISK_SCORE, 3) AS CHURN_RISK, u.OPEN_CLAIMS
                FROM CUSTOMER_360.AI.DT_CHURN_RISK cr
                JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED u ON cr.CUSTOMER_ID = u.CUSTOMER_ID
                WHERE u.OPEN_CLAIMS > 0 AND cr.CHURN_RISK_SCORE >= 0.6
                ORDER BY cr.CHURN_RISK_SCORE DESC LIMIT 15
            """).to_pandas()
            return ("Customers with open claims and high churn risk:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    return call_cortex_llm(question)


# Display chat history
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if i in st.session_state.dataframes:
            st.dataframe(st.session_state.dataframes[i], use_container_width=True, hide_index=True)
        if msg.get("is_llm_fallback"):
            st.caption("Note: This answer is from the AI model, not live Snowflake data. Verify with the dashboards.")

# Chat input
if prompt := st.chat_input("Ask about your customers..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

# Generate response for latest user message
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            text, df, is_live = answer_with_data(st.session_state.messages[-1]["content"])
            st.markdown(text)
            if df is not None:
                st.dataframe(df, use_container_width=True, hide_index=True)
            if not is_live:
                st.caption("Note: This answer is from the AI model, not live Snowflake data. Verify with the dashboards.")

            msg_idx = len(st.session_state.messages)
            st.session_state.messages.append({
                "role": "assistant",
                "content": text,
                "is_llm_fallback": not is_live
            })
            if df is not None:
                st.session_state.dataframes[msg_idx] = df
