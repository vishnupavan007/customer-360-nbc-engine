import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="AI Advisor", page_icon="🤖", layout="wide")

st.title("Customer 360 AI Advisor")
st.caption("Ask natural-language questions about customers, churn risk, sentiment, and next best actions")

session = get_active_session()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Example prompts sidebar
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
        st.rerun()


def call_cortex_analyst(question: str) -> str:
    """Query Cortex using a plain string prompt."""
    try:
        safe_q = question.replace("'", "''")
        result = session.sql(f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'llama3.1-8b',
                'You are a Customer 360 AI Advisor for an insurance and lending company. ' ||
                'Answer questions about customer data. Customer segments: Basic, Standard, Premium, VIP. ' ||
                'Policy types: Auto, Home, Life, Health. Loan types: Mortgage, Auto, Personal, Business. ' ||
                'Churn risk scores range 0-1. Be specific and actionable. ' ||
                'Question: {safe_q}'
            ) AS RESPONSE
        """).collect()
        return result[0]["RESPONSE"] if result else "No response received."
    except Exception as e:
        return f"Error: {str(e)}"


def answer_with_data(question: str) -> str:
    """Try to answer data questions directly with SQL when possible."""
    q_lower = question.lower()

    try:
        # Top churn risk customers
        if "top" in q_lower and "churn" in q_lower:
            df = session.sql("""
                SELECT cr.FULL_NAME, cr.CUSTOMER_SEGMENT,
                       ROUND(cr.CHURN_RISK_SCORE, 3) AS CHURN_RISK,
                       cr.RETENTION_URGENCY,
                       nba.ACTION_TYPE, nba.PRIORITY
                FROM CUSTOMER_360.AI.DT_CHURN_RISK cr
                LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba
                    ON cr.CUSTOMER_ID = nba.CUSTOMER_ID
                WHERE cr.CHURN_RISK_SCORE IS NOT NULL
                ORDER BY cr.CHURN_RISK_SCORE DESC LIMIT 10
            """).to_pandas()
            return f"**Top 10 customers by churn risk:**\n\n{df.to_markdown(index=False)}"

        # Sentiment by segment
        if "sentiment" in q_lower and "segment" in q_lower:
            df = session.sql("""
                SELECT c.CUSTOMER_SEGMENT,
                       ROUND(AVG(s.SENTIMENT_SCORE), 3) AS AVG_SENTIMENT,
                       COUNT(*) AS CALL_COUNT
                FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
                JOIN CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT s ON c.CUSTOMER_ID = s.CUSTOMER_ID
                GROUP BY c.CUSTOMER_SEGMENT ORDER BY AVG_SENTIMENT
            """).to_pandas()
            return f"**Average sentiment by segment:**\n\n{df.to_markdown(index=False)}"

        # Churn distribution
        if "distribution" in q_lower and "churn" in q_lower:
            df = session.sql("""
                SELECT
                    CASE WHEN CHURN_RISK_SCORE >= 0.8 THEN 'Critical (0.8-1.0)'
                         WHEN CHURN_RISK_SCORE >= 0.6 THEN 'High (0.6-0.8)'
                         WHEN CHURN_RISK_SCORE >= 0.4 THEN 'Medium (0.4-0.6)'
                         WHEN CHURN_RISK_SCORE >= 0.2 THEN 'Low (0.2-0.4)'
                         ELSE 'Minimal (0-0.2)'
                    END AS RISK_BUCKET,
                    COUNT(*) AS CUSTOMERS
                FROM CUSTOMER_360.AI.DT_CHURN_RISK
                WHERE CHURN_RISK_SCORE IS NOT NULL
                GROUP BY 1 ORDER BY 1
            """).to_pandas()
            return f"**Churn risk distribution:**\n\n{df.to_markdown(index=False)}"

        # High risk Premium count
        if "premium" in q_lower and ("high" in q_lower or "risk" in q_lower):
            df = session.sql("""
                SELECT COUNT(*) AS HIGH_RISK_PREMIUM
                FROM CUSTOMER_360.AI.DT_CHURN_RISK
                WHERE CHURN_RISK_SCORE >= 0.7 AND CUSTOMER_SEGMENT = 'Premium'
            """).to_pandas()
            count = df["HIGH_RISK_PREMIUM"].iloc[0]
            return f"There are **{count}** high-risk churn customers (score ≥ 0.7) in the Premium segment."

        # NBA for negative sentiment
        if "action" in q_lower and ("negative" in q_lower or "sentiment" in q_lower):
            df = session.sql("""
                SELECT nba.ACTION_TYPE, COUNT(*) AS ACTION_COUNT
                FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba
                WHERE nba.LATEST_SENTIMENT_LABEL = 'Negative'
                  AND nba.ACTION_TYPE IS NOT NULL
                GROUP BY nba.ACTION_TYPE ORDER BY ACTION_COUNT DESC
            """).to_pandas()
            return f"**Most common actions for customers with negative sentiment:**\n\n{df.to_markdown(index=False)}"

        # Complaints
        if "complaint" in q_lower:
            df = session.sql("""
                SELECT COUNT(*) AS CUSTOMERS
                FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED
                WHERE COMPLAINT_COUNT > 2
            """).to_pandas()
            count = df["CUSTOMERS"].iloc[0]
            return f"**{count}** customers have more than 2 complaints."

    except Exception:
        pass

    # Fall back to LLM
    return call_cortex_analyst(question)


# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask about your customers..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

# Generate response for the latest user message
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            response = answer_with_data(st.session_state.messages[-1]["content"])
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
