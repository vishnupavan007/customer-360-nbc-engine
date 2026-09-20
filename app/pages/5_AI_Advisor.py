import streamlit as st
from snowflake.snowpark.context import get_active_session
from utils import apply_theme, theme_sidebar
import datetime
import re

st.set_page_config(page_title="AI Advisor", page_icon="🤖", layout="wide")
apply_theme()

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

if "messages"   not in st.session_state: st.session_state.messages   = []
if "dataframes" not in st.session_state: st.session_state.dataframes = {}
if "msg_source" not in st.session_state: st.session_state.msg_source = {}
if "use_live"   not in st.session_state: st.session_state.use_live   = True
if "last_route" not in st.session_state: st.session_state.last_route = ""

# ── Theme-aware bubble CSS ─────────────────────────────────────────────────────
_dark = st.session_state.get("dark_mode", False)

if _dark:
    _U_BG, _U_TXT = "#1a3a5c", "#E3F2FD"
    _A_BG, _A_TXT = "#1f2235", "#CFD8DC"
    _STATUS_BG, _STATUS_BORDER, _STATUS_TXT = "#1a274480", "#1e3a6e", "#90CAF9"
    _WHO_COLOR = "#29B5E8"
else:
    _U_BG, _U_TXT = "#E3F2FD", "#1A237E"
    _A_BG, _A_TXT = "#F8FAFC", "#1A237E"
    _STATUS_BG, _STATUS_BORDER, _STATUS_TXT = "#EFF8FF", "#90CAF9", "#0D47A1"
    _WHO_COLOR = "#0078A8"

st.markdown(f"""
<style>
.bubble-u {{
    border-radius:12px 12px 4px 12px; padding:14px 18px;
    margin:0 0 12px 20%; border-right:3px solid #29B5E8;
    background:{_U_BG};
}}
.bubble-u .who {{ font-size:0.72rem; font-weight:700; color:{_WHO_COLOR}; margin-bottom:4px; }}
.bubble-u .txt {{ color:{_U_TXT}; line-height:1.5; font-size:0.9rem; }}

.bubble-a {{
    border-radius:12px 12px 12px 4px; padding:14px 18px;
    margin:0 20% 12px 0; border-left:3px solid #29B5E8;
    background:{_A_BG};
}}
.bubble-a .who {{ font-size:0.72rem; font-weight:700; color:{_WHO_COLOR}; margin-bottom:4px; }}
.bubble-a .txt {{
    color:{_A_TXT}; line-height:1.7; font-size:0.9rem;
}}
.bubble-a .txt strong {{ color:{_A_TXT}; font-weight:700; }}
.bubble-a .txt ul {{ margin:6px 0; padding-left:20px; }}
.bubble-a .txt li {{ margin:3px 0; }}
.bubble-a .txt p  {{ margin:4px 0; }}

.bd {{ display:inline-block; padding:1px 8px; border-radius:8px;
      font-size:0.67rem; font-weight:700; margin-left:6px; vertical-align:middle; }}
.bd-agent {{ background:#0D47A130; color:#29B5E8; border:1px solid #29B5E840; }}
.bd-sql   {{ background:#1B5E2030; color:#43A047; border:1px solid #43A04740; }}
.bd-llm   {{ background:#4A148C30; color:#AB47BC; border:1px solid #AB47BC40; }}
.bd-guard {{ background:#B71C1C30; color:#EF5350; border:1px solid #EF535040; }}

.status-bar {{
    border-radius:8px; padding:8px 14px; font-size:0.8rem; margin-bottom:12px;
    background:{_STATUS_BG}; border:1px solid {_STATUS_BORDER}; color:{_STATUS_TXT};
}}
</style>
""", unsafe_allow_html=True)


# ── DataFrame → inline HTML table (embeds inside bubble) ────────────────────
def _df_to_html(df, dark=False):
    bg         = "#1c2235" if dark else "#FFFFFF"
    header_bg  = "#1a3050" if dark else "#E3F2FD"
    text_col   = "#CFD8DC" if dark else "#1A237E"
    muted_col  = "#90A4AE" if dark else "#455A64"
    border     = "#2a2d42" if dark else "#CFD8DC"
    alt_bg     = "#161828" if dark else "#F8FAFC"

    cols = df.columns.tolist()
    th_style = (f"padding:7px 12px;text-align:left;font-size:0.75rem;"
                f"font-weight:700;color:{muted_col};background:{header_bg};"
                f"border-bottom:2px solid {border};white-space:nowrap")
    header = "".join(f"<th style='{th_style}'>{c}</th>" for c in cols)

    rows_html = []
    for idx, (_, row) in enumerate(df.iterrows()):
        row_bg = alt_bg if idx % 2 else bg
        td_style = (f"padding:6px 12px;font-size:0.8rem;color:{text_col};"
                    f"border-bottom:1px solid {border}")
        cells = "".join(f"<td style='{td_style}'>{row[c]}</td>" for c in cols)
        rows_html.append(f"<tr style='background:{row_bg}'>{cells}</tr>")

    return (
        f"<div style='overflow-x:auto;margin-top:10px;border-radius:8px;"
        f"border:1px solid {border};overflow:hidden'>"
        f"<table style='width:100%;border-collapse:collapse;background:{bg}'>"
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        f"</table></div>"
    )


# ── Markdown → HTML converter ──────────────────────────────────────────────────
def _md_to_html(text):
    """Convert common markdown patterns to HTML for rendering inside div bubbles."""
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text, flags=re.DOTALL)
    # Italic (but not inside bold)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)

    lines   = text.split('\n')
    html    = []
    in_ul   = False

    for line in lines:
        stripped = line.strip()
        is_bullet = stripped.startswith('- ') or stripped.startswith('* ')

        if is_bullet:
            if not in_ul:
                html.append('<ul>')
                in_ul = True
            html.append(f'<li>{stripped[2:]}</li>')
        else:
            if in_ul:
                html.append('</ul>')
                in_ul = False
            if stripped == '':
                html.append('<br>')
            else:
                html.append(f'<p>{stripped}</p>')

    if in_ul:
        html.append('</ul>')

    return ''.join(html)


# ── Domain guardrail ──────────────────────────────────────────────────────────
_DOMAIN = {
    "customer","customers","churn","risk","policy","policies","claim","claims",
    "loan","loans","premium","segment","segments","sentiment","action","actions",
    "complaint","complaints","escalation","interactions","retention","vip",
    "basic","standard","score","transcript","insurance","lending","billing",
    "coverage","payment","nba","next best","360","securelife","call",
    "robert","lisa","david","donald","dorothy","kenji","barbara","sarah","joseph",
    "tanaka","ramirez","harris","smith","martin","singh","jones","miller","brown",
}
_REFUSE = "I can only answer questions about SecureLife customer data — churn risk, policies, claims, loans, sentiment, or next best actions."


def in_scope(q): return any(kw in q.lower() for kw in _DOMAIN)


def badge(src):
    m = {"agent":("Cortex Agent","bd-agent"),"sql":("Live SQL","bd-sql"),
         "llm":("LLM","bd-llm"),"guard":("Out of scope","bd-guard")}
    t, c = m.get(src, ("",""))
    return f'<span class="bd {c}">{t}</span>' if t else ""


# ── Agent call (REST, 20s timeout, last 6 turns) ──────────────────────────────
@st.cache_resource
def _ssl_ctx():
    import ssl
    return ssl.create_default_context()


def call_agent(messages):
    try:
        import json, urllib.request
        try:    raw = session._conn._conn
        except: raw = session.connection
        host, token = raw.host, raw.rest.token
        url = (f"https://{host}/api/v2/databases/CUSTOMER_360/schemas/APP"
               "/agents/CUSTOMER_360_AGENT:run")
        recent = messages[-6:]
        api_msgs = []
        for m in recent:
            c = m["content"]
            if isinstance(c, str): c = [{"type":"text","text":c}]
            api_msgs.append({"role":m["role"],"content":c})
        body = json.dumps({"messages":api_msgs,"stream":False}).encode()
        req  = urllib.request.Request(url, body, method="POST",
               headers={"Authorization":f'Snowflake Token="{token}"',
                        "Content-Type":"application/json","Accept":"application/json"})
        with urllib.request.urlopen(req, context=_ssl_ctx(), timeout=20) as r:
            data = json.loads(r.read().decode())
        text = ""
        if "content" in data and isinstance(data["content"], list):
            for item in data["content"]:
                if isinstance(item, dict) and item.get("type") == "text":
                    text += item.get("text","")
        elif "choices" in data and data["choices"]:
            text = data["choices"][0].get("message",{}).get("content","")
        else:
            text = str(data)
        return (text, True) if text else ("No response.", False)
    except Exception as e:
        return (f"Agent error: {e}", False)


# ── SQL fast-path patterns (skip agent for known queries → ~1s response) ──────
_SQL_PATTERNS = [
    ({"top","churn"},            None),
    ({"distribution","churn"},   None),
    ({"sentiment","segment"},    None),
    ({"claim"},                  {"churn","risk"}),
    ({"premium"},                {"high","risk"}),
    ({"complaint"},              None),
]

def _is_sql_fast(q):
    ql = q.lower()
    for required, any_of in _SQL_PATTERNS:
        if all(kw in ql for kw in required):
            if any_of is None or any(kw in ql for kw in any_of):
                return True
    return False


# ── SQL fallback ──────────────────────────────────────────────────────────────
def sql_fallback(question):
    q = question.lower()
    def run(sql): return session.sql(sql).to_pandas()

    if "top" in q and "churn" in q:
        try:
            df = run("""SELECT cr.FULL_NAME, cr.CUSTOMER_SEGMENT,
                ROUND(cr.CHURN_RISK_SCORE,3) AS CHURN_RISK, cr.RETENTION_URGENCY,
                nba.ACTION_TYPE, nba.PRIORITY
                FROM CUSTOMER_360.AI.DT_CHURN_RISK cr
                LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba ON cr.CUSTOMER_ID=nba.CUSTOMER_ID
                WHERE cr.CHURN_RISK_SCORE IS NOT NULL ORDER BY cr.CHURN_RISK_SCORE DESC LIMIT 10""")
            return "**Top 10 customers by churn risk:**", df, True
        except Exception as e: return f"Error: {e}", None, False

    if "distribution" in q and "churn" in q:
        try:
            df = run("""SELECT CASE WHEN CHURN_RISK_SCORE>=0.8 THEN 'Critical'
                WHEN CHURN_RISK_SCORE>=0.6 THEN 'High' WHEN CHURN_RISK_SCORE>=0.4 THEN 'Medium'
                WHEN CHURN_RISK_SCORE>=0.2 THEN 'Low' ELSE 'Minimal' END AS BUCKET,
                COUNT(*) AS CUSTOMERS FROM CUSTOMER_360.AI.DT_CHURN_RISK
                WHERE CHURN_RISK_SCORE IS NOT NULL GROUP BY 1 ORDER BY CUSTOMERS DESC""")
            return "**Churn risk distribution:**", df, True
        except Exception as e: return f"Error: {e}", None, False

    if "sentiment" in q and "segment" in q:
        try:
            df = run("""SELECT c.CUSTOMER_SEGMENT, ROUND(AVG(s.SENTIMENT_SCORE),3) AS AVG_SENTIMENT, COUNT(*) AS CALLS
                FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
                JOIN CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT s ON c.CUSTOMER_ID=s.CUSTOMER_ID
                GROUP BY c.CUSTOMER_SEGMENT ORDER BY AVG_SENTIMENT""")
            return "**Average sentiment by segment:**", df, True
        except Exception as e: return f"Error: {e}", None, False

    if "claim" in q and ("churn" in q or "risk" in q):
        try:
            df = run("""SELECT cr.FULL_NAME, cr.CUSTOMER_SEGMENT,
                ROUND(cr.CHURN_RISK_SCORE,3) AS CHURN_RISK, u.OPEN_CLAIMS
                FROM CUSTOMER_360.AI.DT_CHURN_RISK cr
                JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED u ON cr.CUSTOMER_ID=u.CUSTOMER_ID
                WHERE u.OPEN_CLAIMS>0 AND cr.CHURN_RISK_SCORE>=0.6
                ORDER BY cr.CHURN_RISK_SCORE DESC LIMIT 15""")
            return "**Customers with open claims and high churn risk:**", df, True
        except Exception as e: return f"Error: {e}", None, False

    if "premium" in q and ("high" in q or "risk" in q):
        try:
            df = run("SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE>=0.7 AND CUSTOMER_SEGMENT='Premium'")
            cnt = df['CNT'].iloc[0]
            return f"**{cnt}** high-risk customers (score ≥ 0.7) in the Premium segment.", None, True
        except Exception as e: return f"Error: {e}", None, False

    if "complaint" in q:
        try:
            df = run("""SELECT c.FULL_NAME, c.CUSTOMER_SEGMENT, c.COMPLAINT_COUNT,
                ROUND(cr.CHURN_RISK_SCORE,3) AS CHURN_RISK, nba.ACTION_TYPE, nba.PRIORITY
                FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
                LEFT JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID=cr.CUSTOMER_ID
                LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba ON c.CUSTOMER_ID=nba.CUSTOMER_ID
                WHERE c.COMPLAINT_COUNT>2 ORDER BY c.COMPLAINT_COUNT DESC""")
            return f"**{len(df)} customers** have more than 2 complaints:", df, True
        except Exception as e: return f"Error: {e}", None, False

    try:
        sq = "".join(c for c in question if c.isalnum() or c in " .,?-_'")[:500].replace("'","''")
        res = session.sql(
            f"SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b',"
            f"'You are a Customer 360 advisor for SecureLife insurance. "
            f"Answer concisely. Only answer about customers, churn, policies, claims. Q: {sq}') AS R"
        ).collect()
        return (res[0]["R"] if res else "No response."), None, False
    except Exception as e:
        return f"Could not answer: {e}", None, False


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    theme_sidebar()
    st.divider()
    st.markdown("### AI Advisor")
    st.caption("Snowflake Cortex Agent")
    st.divider()
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages   = []
        st.session_state.dataframes = {}
        st.session_state.msg_source = {}
        st.session_state.last_route = ""
        st.rerun()
    st.divider()
    st.markdown("**Quick examples**")
    for q in [
        "Show top 10 customers by churn risk",
        "Churn risk distribution",
        "Average sentiment by segment",
        "Customers with open claims and high churn risk",
        "How many customers have 2+ complaints?",
    ]:
        if st.button(q, key=q, use_container_width=True):
            st.session_state.messages.append({"role":"user","content":q})
            st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
header_text_color = "#E0E0E0" if _dark else "#1A237E"
st.markdown(
    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:2px">'
    f'<span style="font-size:1.4rem;font-weight:800;color:{header_text_color}">Customer 360 AI Advisor</span>'
    f'<span style="background:#29B5E8;color:#fff;padding:2px 10px;border-radius:8px;'
    f'font-size:0.7rem;font-weight:700">LIVE</span>'
    f'</div>'
    f'<div style="font-size:0.82rem;margin-bottom:14px;color:{_STATUS_TXT}">'
    f'Ask anything about your customers — powered by Snowflake Cortex Agent</div>',
    unsafe_allow_html=True,
)

# ── Status bar ────────────────────────────────────────────────────────────────
route_labels = {
    "agent": "Cortex Agent active — using Semantic View + Search.",
    "sql":   "SQL routing active — using live Snowflake data.",
    "llm":   "LLM mode — using model for general insurance info.",
    "guard": "Question out of scope for this advisor.",
    "":      "Ready. Ask a question about your customers.",
}
route_msg = route_labels.get(st.session_state.last_route, route_labels[""])
col_status, col_toggle = st.columns([3, 1])
with col_status:
    st.markdown(f'<div class="status-bar">ℹ️ &nbsp;{route_msg}</div>', unsafe_allow_html=True)
with col_toggle:
    st.session_state.use_live = st.toggle("Use Live Snowflake Data", value=st.session_state.use_live)

# ── Chat messages ─────────────────────────────────────────────────────────────
empty_color = "#607D8B" if _dark else "#90A4AE"
if not st.session_state.messages:
    st.markdown(
        f'<div style="text-align:center;padding:40px 0;color:{empty_color}">'
        f'<div style="font-size:2.2rem;margin-bottom:8px">💬</div>'
        f'<div style="font-size:0.9rem">No messages yet.<br>'
        f'Use the suggestion chips below or type a question.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    for i, msg in enumerate(st.session_state.messages):
        now = datetime.datetime.now().strftime("%I:%M %p")
        if msg["role"] == "user":
            st.markdown(
                f'<div class="bubble-u">'
                f'<span style="float:right;font-size:0.67rem;opacity:0.5">{now}</span>'
                f'<div class="who">You</div>'
                f'<div class="txt">{msg["content"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            src      = st.session_state.msg_source.get(i, "agent")
            txt_html = _md_to_html(msg["content"])
            tbl_html = ""
            if i in st.session_state.dataframes:
                tbl_html = _df_to_html(st.session_state.dataframes[i], dark=_dark)
            llm_note = (
                "<div style='font-size:0.72rem;opacity:0.6;margin-top:8px'>"
                "Answer from AI model — not live Snowflake data.</div>"
                if src == "llm" else ""
            )
            st.markdown(
                f'<div class="bubble-a">'
                f'<div class="who">AI Advisor {badge(src)}</div>'
                f'<div class="txt">{txt_html}</div>'
                f'{tbl_html}'
                f'{llm_note}'
                f'</div>',
                unsafe_allow_html=True,
            )

# ── Input form ────────────────────────────────────────────────────────────────
with st.form("chat_form", clear_on_submit=True):
    c1, c2 = st.columns([7, 1])
    with c1:
        user_q = st.text_input("q", label_visibility="collapsed",
                               placeholder="Ask about your customers...")
    with c2:
        sent = st.form_submit_button("Ask", type="primary", use_container_width=True)

if sent and user_q and user_q.strip():
    st.session_state.messages.append({"role":"user","content":user_q.strip()})
    st.rerun()

# ── Suggestion chips ──────────────────────────────────────────────────────────
st.markdown("**Quick questions:**")
CHIPS = [
    ("📊", "Show top 10 customers by churn risk"),
    ("🔄", "What is the churn risk distribution?"),
    ("📋", "Customers with open claims and high churn risk"),
    ("👥", "How many high-risk customers are in Premium?"),
]
cols = st.columns(4)
for col, (icon, text) in zip(cols, CHIPS):
    with col:
        if st.button(f"{icon}  {text}", use_container_width=True, key=f"chip_{text}"):
            st.session_state.messages.append({"role":"user","content":text})
            st.rerun()

# ── Generate response ─────────────────────────────────────────────────────────
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_q  = st.session_state.messages[-1]["content"]
    out_idx = len(st.session_state.messages)

    if not in_scope(last_q):
        st.session_state.messages.append({"role":"assistant","content":_REFUSE})
        st.session_state.msg_source[out_idx] = "guard"
        st.session_state.last_route          = "guard"
        st.rerun()

    # Fast path: known SQL patterns bypass the agent (~1s)
    if _is_sql_fast(last_q):
        with st.spinner("Querying Snowflake..."):
            text, df, live = sql_fallback(last_q)
        st.session_state.messages.append({"role":"assistant","content":text})
        src = "sql" if live else "llm"
        st.session_state.msg_source[out_idx] = src
        st.session_state.last_route          = src
        if df is not None:
            st.session_state.dataframes[out_idx] = df
        st.rerun()

    # Slow path: try Cortex Agent (20s), fall back to SQL on failure
    with st.spinner("Asking Cortex Agent..."):
        if st.session_state.use_live:
            agent_text, agent_ok = call_agent(st.session_state.messages)
        else:
            agent_ok, agent_text = False, "Live data disabled."

    if agent_ok and not agent_text.startswith("Agent error"):
        st.session_state.messages.append({"role":"assistant","content":agent_text})
        st.session_state.msg_source[out_idx] = "agent"
        st.session_state.last_route          = "agent"
    else:
        with st.spinner("Querying Snowflake..."):
            text, df, live = sql_fallback(last_q)
        st.session_state.messages.append({"role":"assistant","content":text})
        src = "sql" if live else "llm"
        st.session_state.msg_source[out_idx] = src
        st.session_state.last_route          = src
        if df is not None:
            st.session_state.dataframes[out_idx] = df

    st.rerun()
