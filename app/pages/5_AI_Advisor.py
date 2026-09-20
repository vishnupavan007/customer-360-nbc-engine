import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="AI Advisor", page_icon="🤖", layout="wide")

st.title("Customer 360 AI Advisor")
st.caption("Conversational AI powered by Cortex Agent with Semantic View + Search")

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

AGENT_NAME = "CUSTOMER_360.APP.CUSTOMER_360_AGENT"

if "messages" not in st.session_state:
    st.session_state.messages = []
if "dataframes" not in st.session_state:
    st.session_state.dataframes = {}

with st.sidebar:
    st.header("Example Questions")
    examples = [
        "How many high-risk churn customers are in the Premium segment?",
        "What is the average sentiment score by customer segment?",
        "Show me top 10 customers by churn risk with their next best action",
        "What are the most common actions for customers with negative sentiment?",
        "How many customers have more than 2 complaints?",
        "Get the complaint details",
        "What is the churn risk distribution across segments?",
        "Which customers have open claims and high churn risk?",
        "Search call transcripts about policy cancellation",
        "What did customers say about billing issues?",
    ]
    for ex in examples:
        if st.button(ex, key=ex):
            st.session_state.messages.append({"role": "user", "content": ex})
            st.experimental_rerun()

    st.markdown("---")
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.dataframes = {}
        st.experimental_rerun()

MAX_QUESTION_LENGTH = 500

# Domain keywords — question must contain at least one to be in scope
_DOMAIN_KEYWORDS = {
    "customer", "customers", "churn", "risk", "policy", "policies",
    "claim", "claims", "loan", "loans", "premium", "segment", "segments",
    "sentiment", "action", "actions", "complaint", "complaints",
    "escalation", "escalations", "interaction", "interactions",
    "retention", "vip", "basic", "standard", "score", "transcript",
    "transcripts", "renewal", "renewals", "insurance", "lending",
    "billing", "coverage", "payment", "nba", "next best", "360",
    "securelife", "overdue", "high risk", "churn risk", "call",
    "agent", "robert", "lisa", "david", "donald", "dorothy",
    "kenji", "barbara", "sarah", "joseph", "tanaka", "ramirez",
    "harris", "smith", "martin", "singh", "jones", "miller", "brown",
}

_OUT_OF_SCOPE_REPLY = (
    "I can only answer questions about customers, churn risk, policies, "
    "claims, loans, interactions, sentiment, and next best actions for "
    "SecureLife's insurance and lending portfolio. "
    "Please ask a question related to your customer data."
)


def is_in_scope(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in _DOMAIN_KEYWORDS)


def call_cortex_agent(messages: list) -> tuple[str, bool]:
    """Call the Cortex Agent via SQL — SiS compatible."""
    try:
        import json

        # Build the messages array for the agent
        api_messages = []
        for m in messages:
            c = m["content"]
            if isinstance(c, str):
                c = [{"type": "text", "text": c}]
            api_messages.append({"role": m["role"], "content": c})

        payload = json.dumps({"messages": api_messages, "stream": False})
        safe_payload = payload.replace("'", "''")

        result = session.sql(
            f"SELECT SNOWFLAKE.CORTEX.AGENT('{AGENT_NAME}', "
            f"PARSE_JSON('{safe_payload}')) AS RESPONSE"
        ).collect()

        if result and result[0]["RESPONSE"]:
            resp = result[0]["RESPONSE"]
            # Parse the response — may be JSON string or plain text
            try:
                data = json.loads(resp) if isinstance(resp, str) else resp
                text = ""
                if isinstance(data, dict) and "content" in data:
                    for item in data["content"]:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text += item.get("text", "")
                elif isinstance(data, dict) and "choices" in data:
                    text = data["choices"][0].get("message", {}).get("content", "")
                else:
                    text = str(data)
                return (text, True) if text else ("Empty response from agent.", False)
            except (json.JSONDecodeError, TypeError):
                return (str(resp), True)
        return ("Empty response from agent.", False)
    except Exception as e:
        return (f"Agent error: {str(e)}", False)


def call_cortex_sql_fallback(question: str) -> tuple[str, object, bool]:
    """SQL-based fallback for when agent is unavailable."""
    q = question.lower()

    def run(sql):
        return session.sql(sql).to_pandas()

    if "top" in q and "churn" in q:
        try:
            df = run("""SELECT cr.FULL_NAME, cr.CUSTOMER_SEGMENT, ROUND(cr.CHURN_RISK_SCORE,3) AS CHURN_RISK,
                       cr.RETENTION_URGENCY, nba.ACTION_TYPE, nba.PRIORITY
                FROM CUSTOMER_360.AI.DT_CHURN_RISK cr
                LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba ON cr.CUSTOMER_ID=nba.CUSTOMER_ID
                WHERE cr.CHURN_RISK_SCORE IS NOT NULL ORDER BY cr.CHURN_RISK_SCORE DESC LIMIT 10""")
            return ("Top 10 customers by churn risk:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "sentiment" in q and "segment" in q:
        try:
            df = run("""SELECT c.CUSTOMER_SEGMENT, ROUND(AVG(s.SENTIMENT_SCORE),3) AS AVG_SENTIMENT, COUNT(*) AS CALLS
                FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
                JOIN CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT s ON c.CUSTOMER_ID=s.CUSTOMER_ID
                GROUP BY c.CUSTOMER_SEGMENT ORDER BY AVG_SENTIMENT""")
            return ("Average sentiment by segment:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "distribution" in q and "churn" in q:
        try:
            df = run("""SELECT CASE WHEN CHURN_RISK_SCORE>=0.8 THEN 'Critical (0.8-1.0)'
                         WHEN CHURN_RISK_SCORE>=0.6 THEN 'High (0.6-0.8)'
                         WHEN CHURN_RISK_SCORE>=0.4 THEN 'Medium (0.4-0.6)'
                         WHEN CHURN_RISK_SCORE>=0.2 THEN 'Low (0.2-0.4)'
                         ELSE 'Minimal (0-0.2)' END AS BUCKET, COUNT(*) AS CUSTOMERS
                FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE IS NOT NULL GROUP BY 1 ORDER BY 1""")
            return ("Churn risk distribution:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "premium" in q and ("high" in q or "risk" in q):
        try:
            df = run("SELECT COUNT(*) AS HIGH_RISK_PREMIUM FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE>=0.7 AND CUSTOMER_SEGMENT='Premium'")
            return (f"There are **{df['HIGH_RISK_PREMIUM'].iloc[0]}** high-risk churn customers (score >= 0.7) in Premium.", None, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "action" in q and ("negative" in q or "sentiment" in q):
        try:
            df = run("""SELECT nba.ACTION_TYPE, COUNT(*) AS ACTION_COUNT
                FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba
                WHERE nba.LATEST_SENTIMENT_LABEL='Negative' AND nba.ACTION_TYPE IS NOT NULL
                GROUP BY nba.ACTION_TYPE ORDER BY ACTION_COUNT DESC""")
            return ("Most common actions for customers with negative sentiment:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "complaint" in q:
        if any(w in q for w in ["detail", "history", "list", "show", "what", "interaction", "record", "get"]):
            try:
                df = run("""SELECT c.FULL_NAME, c.CUSTOMER_SEGMENT, i.CHANNEL, i.SUBJECT,
                               i.NOTES, i.RESOLUTION_STATUS, i.INTERACTION_DATE
                        FROM CUSTOMER_360.CLEAN.DT_INTERACTIONS i
                        JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c ON i.CUSTOMER_ID=c.CUSTOMER_ID
                        WHERE i.INTERACTION_TYPE='Complaint' AND c.COMPLAINT_COUNT>2
                        ORDER BY c.COMPLAINT_COUNT DESC, i.INTERACTION_DATE DESC""")
                return (f"Complaint interactions for customers with >2 complaints ({len(df)} records):", df, True)
            except Exception as e:
                return (f"Error: {e}", None, False)
        else:
            try:
                df = run("""SELECT c.FULL_NAME, c.CUSTOMER_SEGMENT, c.COMPLAINT_COUNT, c.ESCALATION_COUNT,
                               ROUND(cr.CHURN_RISK_SCORE,3) AS CHURN_RISK, cr.RETENTION_URGENCY,
                               nba.ACTION_TYPE, nba.PRIORITY, nba.ACTION_DESCRIPTION
                        FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
                        LEFT JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID=cr.CUSTOMER_ID
                        LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba ON c.CUSTOMER_ID=nba.CUSTOMER_ID
                        WHERE c.COMPLAINT_COUNT>2 ORDER BY c.COMPLAINT_COUNT DESC, cr.CHURN_RISK_SCORE DESC""")
                return (f"**{len(df)}** customers have more than 2 complaints:", df, True)
            except Exception as e:
                return (f"Error: {e}", None, False)

    if "claim" in q and ("churn" in q or "risk" in q):
        try:
            df = run("""SELECT cr.FULL_NAME, cr.CUSTOMER_SEGMENT, ROUND(cr.CHURN_RISK_SCORE,3) AS CHURN_RISK, u.OPEN_CLAIMS
                FROM CUSTOMER_360.AI.DT_CHURN_RISK cr
                JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED u ON cr.CUSTOMER_ID=u.CUSTOMER_ID
                WHERE u.OPEN_CLAIMS>0 AND cr.CHURN_RISK_SCORE>=0.6
                ORDER BY cr.CHURN_RISK_SCORE DESC LIMIT 15""")
            return ("Customers with open claims and high churn risk:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    # LLM fallback — only reached for in-scope questions (guardrail already checked upstream)
    try:
        safe_q = "".join(c for c in question if c.isalnum() or c in " .,?-_'")[:MAX_QUESTION_LENGTH].replace("'", "''")
        result = session.sql(
            f"SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b',"
            f" 'You are a Customer 360 AI Advisor ONLY for SecureLife insurance and lending. "
            f"You MUST refuse any question not about customers, churn, policies, claims, loans, "
            f"sentiment, or next best actions. Reply: I can only answer questions about customer data. "
            f"Segments: Basic/Standard/Premium/VIP. Churn risk 0-1. "
            f"Question: {safe_q}') AS RESPONSE"
        ).collect()
        return (result[0]["RESPONSE"] if result else "No response.", None, False)
    except Exception as e:
        return (f"Unable to answer: {str(e)}", None, False)


# Display chat history using markdown (no st.chat_message — unavailable in SiS)
for i, msg in enumerate(st.session_state.messages):
    role = msg["role"]
    prefix = "**You:**" if role == "user" else "**Assistant:**"
    st.markdown(f"{prefix} {msg['content']}")
    if i in st.session_state.dataframes:
        st.dataframe(st.session_state.dataframes[i])
    if msg.get("is_llm_fallback"):
        st.caption("Note: This answer is from the AI model, not live Snowflake data.")

st.markdown("---")

# Chat input using text_input + button (no st.chat_input — unavailable in SiS)
input_col, btn_col = st.columns([5, 1])
with input_col:
    prompt = st.text_input("Ask about your customers...", key="user_input", label_visibility="collapsed")
with btn_col:
    send = st.button("Send")

if send and prompt and prompt.strip():
    st.session_state.messages.append({"role": "user", "content": prompt.strip()})

# Generate response for latest user message
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_question = st.session_state.messages[-1]["content"]

    # Guardrail: block off-topic questions before reaching any LLM
    if not is_in_scope(last_question):
        refusal = _OUT_OF_SCOPE_REPLY
        st.warning(refusal)
        st.session_state.messages.append({"role": "assistant", "content": refusal})
    else:
        with st.spinner("Analyzing via Cortex Agent..."):
            # Try Cortex Agent first
            agent_text, agent_success = call_cortex_agent(st.session_state.messages)

            if agent_success and agent_text and not agent_text.startswith("Agent error"):
                st.markdown(f"**Assistant:** {agent_text}")
                msg_idx = len(st.session_state.messages)
                st.session_state.messages.append({"role": "assistant", "content": agent_text})
            else:
                # Fall back to SQL routing
                if agent_text.startswith("Agent error"):
                    st.caption(f"Agent unavailable, using SQL routing. ({agent_text})")
                text, df, is_live = call_cortex_sql_fallback(st.session_state.messages[-1]["content"])
                st.markdown(f"**Assistant:** {text}")
                if df is not None:
                    st.dataframe(df)
                if not is_live:
                    st.caption("Note: This answer is from the AI model, not live Snowflake data.")
                msg_idx = len(st.session_state.messages)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": text,
                    "is_llm_fallback": not is_live
                })
                if df is not None:
                    st.session_state.dataframes[msg_idx] = df
