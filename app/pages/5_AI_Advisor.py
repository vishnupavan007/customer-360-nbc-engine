import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="AI Advisor", page_icon="🤖", layout="wide")

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Chat bubbles */
.bubble-user {
    background: #E3F2FD;
    border-radius: 16px 16px 4px 16px;
    padding: 10px 16px;
    margin: 8px 0 4px 15%;
    border-right: 3px solid #1565C0;
}
.bubble-user .role { font-size:0.72rem; font-weight:700; color:#1565C0; margin-bottom:4px; }
.bubble-user .text { color:#1A237E; line-height:1.5; }

.bubble-assistant {
    background: #FAFAFA;
    border-radius: 16px 16px 16px 4px;
    padding: 10px 16px;
    margin: 4px 15% 8px 0;
    border-left: 3px solid #29B5E8;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.bubble-assistant .role { font-size:0.72rem; font-weight:700; color:#29B5E8; margin-bottom:4px; }
.bubble-assistant .text { color:#262730; line-height:1.6; }

/* Badges */
.badge-agent { background:#E3F2FD; color:#0D47A1; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:700; margin-left:6px; }
.badge-sql   { background:#E8F5E9; color:#1B5E20; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:700; margin-left:6px; }
.badge-llm   { background:#FFF8E1; color:#F57F17; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:700; margin-left:6px; }
.badge-warn  { background:#FFEBEE; color:#B71C1C; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:700; margin-left:6px; }

/* Input row */
.stTextInput > div > input { border-radius: 20px !important; padding: 10px 16px !important; }

/* Welcome card */
.welcome-card {
    background: linear-gradient(135deg, #E3F2FD 0%, #F3E5F5 100%);
    border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;
    border-left: 4px solid #29B5E8;
}
.welcome-title { font-size:1.1rem; font-weight:700; color:#11567F; margin-bottom:6px; }
.welcome-sub   { font-size:0.85rem; color:#546E7A; }

/* Sidebar example groups */
.ex-group { font-size:0.7rem; font-weight:700; color:#90A4AE;
    text-transform:uppercase; letter-spacing:.08em; margin: 10px 0 4px 0; }
</style>
""", unsafe_allow_html=True)

AGENT_NAME = "CUSTOMER_360.APP.CUSTOMER_360_AGENT"

if "messages" not in st.session_state:
    st.session_state.messages = []
if "dataframes" not in st.session_state:
    st.session_state.dataframes = {}
if "msg_meta" not in st.session_state:
    st.session_state.msg_meta = {}

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="welcome-card">'
        '<div class="welcome-title">Cortex AI Advisor</div>'
        '<div class="welcome-sub">Powered by Cortex Agent<br>'
        'Semantic View + Search</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    EXAMPLES = {
        "Churn & Risk": [
            "Show me top 10 customers by churn risk",
            "What is the churn risk distribution?",
            "Which customers have open claims and high churn risk?",
            "How many high-risk customers are in the Premium segment?",
        ],
        "Sentiment": [
            "What is the average sentiment score by segment?",
            "What are the most common actions for negative sentiment?",
            "Search call transcripts about policy cancellation",
            "What did customers say about billing issues?",
        ],
        "Complaints": [
            "How many customers have more than 2 complaints?",
            "Get the complaint details",
        ],
    }

    for group, questions in EXAMPLES.items():
        st.markdown(f'<div class="ex-group">{group}</div>', unsafe_allow_html=True)
        for q in questions:
            if st.button(q, key=q, use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": q})
                st.rerun()

    st.divider()
    if st.button("Clear Conversation", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.session_state.dataframes = {}
        st.session_state.msg_meta = {}
        st.rerun()

    st.caption(f"Session messages: {len(st.session_state.messages)}")

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    '<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">'
    '<span style="font-size:1.5rem;font-weight:800;color:#11567F">Customer 360 AI Advisor</span>'
    '<span style="background:#29B5E8;color:white;padding:2px 10px;border-radius:10px;'
    'font-size:0.72rem;font-weight:700">LIVE</span>'
    '</div>'
    '<div style="color:#78909C;font-size:0.85rem;margin-bottom:16px">'
    'Ask anything about your customers — powered by Snowflake Cortex Agent</div>',
    unsafe_allow_html=True,
)

# ── Domain guardrail ──────────────────────────────────────────────────────────
MAX_QUESTION_LENGTH = 500

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
    "SecureLife's insurance and lending portfolio."
)


def is_in_scope(q: str) -> bool:
    return any(kw in q.lower() for kw in _DOMAIN_KEYWORDS)


# ── Agent + fallback logic ────────────────────────────────────────────────────
def call_cortex_agent(messages: list) -> tuple[str, bool]:
    try:
        import json
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
                return (text, True) if text else ("Empty response.", False)
            except (json.JSONDecodeError, TypeError):
                return (str(resp), True)
        return ("Empty response.", False)
    except Exception as e:
        return (f"Agent error: {str(e)}", False)


def call_cortex_sql_fallback(question: str) -> tuple[str, object, bool]:
    q = question.lower()

    def run(sql):
        return session.sql(sql).to_pandas()

    if "top" in q and "churn" in q:
        try:
            df = run("""SELECT cr.FULL_NAME, cr.CUSTOMER_SEGMENT,
                       ROUND(cr.CHURN_RISK_SCORE,3) AS CHURN_RISK,
                       cr.RETENTION_URGENCY, nba.ACTION_TYPE, nba.PRIORITY
                FROM CUSTOMER_360.AI.DT_CHURN_RISK cr
                LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba ON cr.CUSTOMER_ID=nba.CUSTOMER_ID
                WHERE cr.CHURN_RISK_SCORE IS NOT NULL
                ORDER BY cr.CHURN_RISK_SCORE DESC LIMIT 10""")
            return ("Top 10 customers by churn risk:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "sentiment" in q and "segment" in q:
        try:
            df = run("""SELECT c.CUSTOMER_SEGMENT,
                       ROUND(AVG(s.SENTIMENT_SCORE),3) AS AVG_SENTIMENT, COUNT(*) AS CALLS
                FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
                JOIN CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT s ON c.CUSTOMER_ID=s.CUSTOMER_ID
                GROUP BY c.CUSTOMER_SEGMENT ORDER BY AVG_SENTIMENT""")
            return ("Average sentiment by segment:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "distribution" in q and "churn" in q:
        try:
            df = run("""SELECT
                CASE WHEN CHURN_RISK_SCORE>=0.8 THEN 'Critical (0.8-1.0)'
                     WHEN CHURN_RISK_SCORE>=0.6 THEN 'High (0.6-0.8)'
                     WHEN CHURN_RISK_SCORE>=0.4 THEN 'Medium (0.4-0.6)'
                     WHEN CHURN_RISK_SCORE>=0.2 THEN 'Low (0.2-0.4)'
                     ELSE 'Minimal (0-0.2)' END AS BUCKET, COUNT(*) AS CUSTOMERS
                FROM CUSTOMER_360.AI.DT_CHURN_RISK
                WHERE CHURN_RISK_SCORE IS NOT NULL GROUP BY 1 ORDER BY 1""")
            return ("Churn risk distribution:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "premium" in q and ("high" in q or "risk" in q):
        try:
            df = run("SELECT COUNT(*) AS HIGH_RISK_PREMIUM FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE>=0.7 AND CUSTOMER_SEGMENT='Premium'")
            return (f"There are **{df['HIGH_RISK_PREMIUM'].iloc[0]}** high-risk customers (score ≥ 0.7) in Premium.", None, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    if "action" in q and ("negative" in q or "sentiment" in q):
        try:
            df = run("""SELECT nba.ACTION_TYPE, COUNT(*) AS ACTION_COUNT
                FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba
                WHERE nba.LATEST_SENTIMENT_LABEL='Negative' AND nba.ACTION_TYPE IS NOT NULL
                GROUP BY nba.ACTION_TYPE ORDER BY ACTION_COUNT DESC""")
            return ("Most common actions for negative sentiment customers:", df, True)
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
                df = run("""SELECT c.FULL_NAME, c.CUSTOMER_SEGMENT, c.COMPLAINT_COUNT,
                               c.ESCALATION_COUNT, ROUND(cr.CHURN_RISK_SCORE,3) AS CHURN_RISK,
                               cr.RETENTION_URGENCY, nba.ACTION_TYPE, nba.PRIORITY, nba.ACTION_DESCRIPTION
                        FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
                        LEFT JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID=cr.CUSTOMER_ID
                        LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba ON c.CUSTOMER_ID=nba.CUSTOMER_ID
                        WHERE c.COMPLAINT_COUNT>2
                        ORDER BY c.COMPLAINT_COUNT DESC, cr.CHURN_RISK_SCORE DESC""")
                return (f"**{len(df)}** customers have more than 2 complaints:", df, True)
            except Exception as e:
                return (f"Error: {e}", None, False)

    if "claim" in q and ("churn" in q or "risk" in q):
        try:
            df = run("""SELECT cr.FULL_NAME, cr.CUSTOMER_SEGMENT,
                       ROUND(cr.CHURN_RISK_SCORE,3) AS CHURN_RISK, u.OPEN_CLAIMS
                FROM CUSTOMER_360.AI.DT_CHURN_RISK cr
                JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED u ON cr.CUSTOMER_ID=u.CUSTOMER_ID
                WHERE u.OPEN_CLAIMS>0 AND cr.CHURN_RISK_SCORE>=0.6
                ORDER BY cr.CHURN_RISK_SCORE DESC LIMIT 15""")
            return ("Customers with open claims and high churn risk:", df, True)
        except Exception as e:
            return (f"Error: {e}", None, False)

    # LLM fallback
    try:
        safe_q = "".join(c for c in question if c.isalnum() or c in " .,?-_'")[:MAX_QUESTION_LENGTH].replace("'", "''")
        result = session.sql(
            f"SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b',"
            f" 'You are a Customer 360 AI Advisor ONLY for SecureLife insurance and lending. "
            f"Refuse any off-topic question. "
            f"Segments: Basic/Standard/Premium/VIP. Churn risk 0-1. "
            f"Question: {safe_q}') AS RESPONSE"
        ).collect()
        return (result[0]["RESPONSE"] if result else "No response.", None, False)
    except Exception as e:
        return (f"Unable to answer: {str(e)}", None, False)


# ── Welcome message when no messages yet ─────────────────────────────────────
if not st.session_state.messages:
    st.markdown(
        '<div style="text-align:center;padding:40px 20px;color:#90A4AE;">'
        '<div style="font-size:2.5rem;margin-bottom:12px">💬</div>'
        '<div style="font-size:1rem;font-weight:600;color:#546E7A;margin-bottom:6px">'
        'Start a conversation</div>'
        '<div style="font-size:0.85rem">Ask about customers, churn risk, sentiment, '
        'or next best actions.<br>Use the example questions in the sidebar to get started.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

# ── Render chat history ───────────────────────────────────────────────────────
for i, msg in enumerate(st.session_state.messages):
    role = msg["role"]
    content = msg["content"]
    meta = st.session_state.msg_meta.get(i, {})

    if role == "user":
        st.markdown(
            f'<div class="bubble-user">'
            f'<div class="role">You</div>'
            f'<div class="text">{content}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        # Pick badge based on how answer was generated
        source = meta.get("source", "agent")
        badge_map = {
            "agent": '<span class="badge-agent">Cortex Agent</span>',
            "sql":   '<span class="badge-sql">SQL</span>',
            "llm":   '<span class="badge-llm">LLM</span>',
            "guard": '<span class="badge-warn">Out of scope</span>',
        }
        badge = badge_map.get(source, "")

        st.markdown(
            f'<div class="bubble-assistant">'
            f'<div class="role">AI Advisor {badge}</div>'
            f'<div class="text">{content}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if i in st.session_state.dataframes:
            st.dataframe(
                st.session_state.dataframes[i],
                use_container_width=True,
                hide_index=True,
            )
        if source == "llm":
            st.caption("This answer is from the AI model, not live Snowflake data.")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.divider()

# ── Input row ─────────────────────────────────────────────────────────────────
input_col, btn_col = st.columns([6, 1])
with input_col:
    prompt = st.text_input(
        "Ask about your customers...",
        key="user_input",
        label_visibility="collapsed",
        placeholder="e.g. Show top 10 customers by churn risk",
    )
with btn_col:
    send = st.button("Ask", type="primary", use_container_width=True)

if send and prompt and prompt.strip():
    st.session_state.messages.append({"role": "user", "content": prompt.strip()})
    st.rerun()

# ── Generate response for latest unanswered user message ─────────────────────
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_q = st.session_state.messages[-1]["content"]
    msg_idx = len(st.session_state.messages)

    if not is_in_scope(last_q):
        st.markdown(
            f'<div class="bubble-assistant">'
            f'<div class="role">AI Advisor <span class="badge-warn">Out of scope</span></div>'
            f'<div class="text">{_OUT_OF_SCOPE_REPLY}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.session_state.messages.append({"role": "assistant", "content": _OUT_OF_SCOPE_REPLY})
        st.session_state.msg_meta[msg_idx] = {"source": "guard"}
    else:
        with st.spinner("Analyzing via Cortex Agent..."):
            agent_text, agent_success = call_cortex_agent(st.session_state.messages)

        if agent_success and agent_text and not agent_text.startswith("Agent error"):
            st.markdown(
                f'<div class="bubble-assistant">'
                f'<div class="role">AI Advisor <span class="badge-agent">Cortex Agent</span></div>'
                f'<div class="text">{agent_text}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.session_state.messages.append({"role": "assistant", "content": agent_text})
            st.session_state.msg_meta[msg_idx] = {"source": "agent"}
        else:
            if agent_text.startswith("Agent error"):
                st.caption(f"Using SQL routing ({agent_text[:80]}...)")
            text, df, is_live = call_cortex_sql_fallback(last_q)
            source = "sql" if is_live else "llm"
            badge_map = {"sql": '<span class="badge-sql">SQL</span>', "llm": '<span class="badge-llm">LLM</span>'}
            st.markdown(
                f'<div class="bubble-assistant">'
                f'<div class="role">AI Advisor {badge_map[source]}</div>'
                f'<div class="text">{text}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if df is not None:
                st.dataframe(df, use_container_width=True, hide_index=True)
            if not is_live:
                st.caption("This answer is from the AI model, not live Snowflake data.")
            st.session_state.messages.append({"role": "assistant", "content": text, "is_llm_fallback": not is_live})
            st.session_state.msg_meta[msg_idx] = {"source": source}
            if df is not None:
                st.session_state.dataframes[msg_idx] = df
