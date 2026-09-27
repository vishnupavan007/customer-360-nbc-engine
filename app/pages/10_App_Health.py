import streamlit as st
from snowflake.snowpark.context import get_active_session
import time
import pandas as pd
from utils import apply_theme, theme_sidebar

st.set_page_config(page_title="App Health", page_icon="🩺", layout="wide")
apply_theme()

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

with st.sidebar:
    theme_sidebar()
    st.divider()
    auto_run = st.checkbox("Auto-run on load", value=True)
    st.caption("Runs all page probes and reports PASS / FAIL with response times.")

st.title("App Health Check")
st.caption("Live probe of every page's core queries — verifies data is reachable and formatted correctly")

# ─── Probe definitions ─────────────────────────────────────────────────────
# Each probe: (page_num, page_name, probe_name, sql, min_rows, description)
PROBES = [
    # ── Home (app.py) ──────────────────────────────────────────────────────
    (0, "Home", "Customer count KPI",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED",
     1, "Unified customer table is readable"),

    (0, "Home", "High churn KPI",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE >= 0.7",
     0, "Churn risk DT returns high-risk count"),

    (0, "Home", "High priority actions KPI",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE PRIORITY = 'High'",
     0, "NBA DT returns high-priority actions"),

    (0, "Home", "Documents processed KPI",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_DOCUMENT_EXTRACTED",
     0, "Document extracted DT is readable"),

    # ── Page 1: Customer 360 View ───────────────────────────────────────────
    (1, "Customer 360", "Customer search query",
     "SELECT CUSTOMER_ID, FULL_NAME, CUSTOMER_SEGMENT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED LIMIT 10",
     1, "Unified view returns customer rows"),

    (1, "Customer 360", "Interaction timeline",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_INTERACTION_TIMELINE",
     1, "Timeline DT returns events"),

    (1, "Customer 360", "Claims data join",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_CHURN_RISK cr JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c ON cr.CUSTOMER_ID = c.CUSTOMER_ID",
     1, "Churn-to-customer join resolves"),

    # ── Page 2: Churn Risk ──────────────────────────────────────────────────
    (2, "Churn Risk", "Segment list for filter",
     "SELECT DISTINCT CUSTOMER_SEGMENT FROM CUSTOMER_360.AI.DT_CHURN_RISK ORDER BY 1",
     1, "Segments available for sidebar filter"),

    (2, "Churn Risk", "Churn score distribution",
     "SELECT RETENTION_URGENCY, COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_CHURN_RISK GROUP BY 1 ORDER BY 1",
     1, "Urgency breakdown query runs"),

    (2, "Churn Risk", "Top churn customers",
     "SELECT FULL_NAME, CHURN_RISK_SCORE FROM CUSTOMER_360.AI.DT_CHURN_RISK ORDER BY CHURN_RISK_SCORE DESC LIMIT 10",
     1, "Top-N churn table renders"),

    # ── Page 3: Sentiment Analysis ──────────────────────────────────────────
    (3, "Sentiment", "KPI aggregation",
     "SELECT COUNT(*) AS TOTAL, ROUND(AVG(SENTIMENT_SCORE),3) AS AVG_SENT, SUM(CASE WHEN SENTIMENT_LABEL='Negative' THEN 1 ELSE 0 END) AS NEG FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT",
     1, "Sentiment KPI aggregation returns a row"),

    (3, "Sentiment", "Distribution by label",
     "SELECT SENTIMENT_LABEL, COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT GROUP BY 1",
     1, "Label breakdown query runs"),

    (3, "Sentiment", "Trend over time",
     "SELECT DATE_TRUNC('WEEK', CALL_DATE) AS WK, ROUND(AVG(SENTIMENT_SCORE),3) AS AVG_S FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT GROUP BY 1 ORDER BY 1 LIMIT 20",
     1, "Weekly sentiment trend query runs"),

    # ── Page 4: Next Best Action ────────────────────────────────────────────
    (4, "Next Best Action", "Action types for filter",
     "SELECT DISTINCT ACTION_TYPE FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE ACTION_TYPE IS NOT NULL ORDER BY 1",
     1, "Action type list available"),

    (4, "Next Best Action", "NBA table rows",
     "SELECT FULL_NAME, ACTION_TYPE, PRIORITY FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE PRIORITY='High' LIMIT 20",
     1, "High-priority NBA rows render"),

    (4, "Next Best Action", "Action mix chart",
     "SELECT ACTION_TYPE, COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION GROUP BY 1 ORDER BY CNT DESC",
     1, "Action type distribution query runs"),

    # ── Page 5: AI Advisor ──────────────────────────────────────────────────
    (5, "AI Advisor", "Context data load",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED WHERE COMPLAINT_COUNT > 0",
     1, "Customer complaint context available"),

    (5, "AI Advisor", "CORTEX.COMPLETE probe",
     "SELECT SNOWFLAKE.CORTEX.COMPLETE('snowflake-arctic', 'Reply with the single word OK') AS REPLY",
     1, "LLM endpoint is reachable"),

    (5, "AI Advisor", "AI churn context",
     "SELECT FULL_NAME, RETENTION_URGENCY, CHURN_RISK_SCORE FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE RETENTION_URGENCY='Critical' LIMIT 5",
     0, "Critical retention context available"),

    # ── Page 6: Operations Dashboard ────────────────────────────────────────
    (6, "Operations", "Layer row counts",
     "SELECT TABLE_SCHEMA AS LAYER, COUNT(*) AS TABLES FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA IN ('RAW','CLEAN','CURATED','AI','APP') GROUP BY 1",
     1, "Information schema layer summary runs"),

    (6, "Operations", "Dynamic table health",
     "SHOW DYNAMIC TABLES IN DATABASE CUSTOMER_360",
     1, "Dynamic table list is available"),

    (6, "Operations", "Cortex Search service",
     "SHOW CORTEX SEARCH SERVICES IN SCHEMA CUSTOMER_360.APP",
     1, "Cortex Search service is registered"),

    # ── Page 7: Document Intelligence ───────────────────────────────────────
    (7, "Documents", "Document count KPIs",
     "SELECT COUNT(*) AS TOTAL, SUM(CASE WHEN DOCUMENT_TYPE='Claim Form' THEN 1 ELSE 0 END) AS CLAIMS FROM CUSTOMER_360.AI.DT_DOCUMENT_EXTRACTED",
     1, "Document KPI aggregation runs"),

    (7, "Documents", "Extracted fields table",
     "SELECT FILE_NAME, DOCUMENT_TYPE, REFERENCE_NUMBER, AMOUNT FROM CUSTOMER_360.AI.DT_DOCUMENT_EXTRACTED LIMIT 10",
     1, "Extracted document fields render"),

    (7, "Documents", "Document-customer cross-ref",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED WHERE TOTAL_DOCUMENTS > 0",
     1, "Documents linked to customers"),

    # ── Page 8: What-If Simulator ────────────────────────────────────────────
    (8, "What-If Simulator", "Health score DT",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_CUSTOMER_HEALTH_SCORE",
     1, "Health score DT has rows"),

    (8, "What-If Simulator", "Customer + churn join",
     "SELECT c.FULL_NAME, cr.CHURN_RISK_SCORE, h.HEALTH_SCORE FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c LEFT JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID=cr.CUSTOMER_ID LEFT JOIN CUSTOMER_360.AI.DT_CUSTOMER_HEALTH_SCORE h ON c.CUSTOMER_ID=h.CUSTOMER_ID LIMIT 5",
     1, "3-way join for What-If page resolves"),

    (8, "What-If Simulator", "CORTEX.COMPLETE prediction",
     "SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-7b', 'What is 2+2? Reply with one word.') AS REPLY",
     1, "Prediction LLM call succeeds"),

    # ── Page 9: Data Lineage ─────────────────────────────────────────────────
    (9, "Data Lineage", "DT count and state",
     "SELECT SCHEDULING_STATE, COUNT(*) AS CNT FROM (SHOW DYNAMIC TABLES IN DATABASE CUSTOMER_360) GROUP BY 1",
     1, "Dynamic table scheduling states available"),

    (9, "Data Lineage", "Layer size totals",
     "SELECT TABLE_SCHEMA, SUM(ROW_COUNT) AS TOTAL_ROWS FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA IN ('RAW','CLEAN','CURATED','AI','APP') GROUP BY 1",
     1, "Layer row count aggregation runs"),

    (9, "Data Lineage", "Pipeline table inventory",
     "SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA IN ('RAW','CLEAN','CURATED','AI','APP') ORDER BY 1, 2",
     1, "Full table inventory renders"),
]

# ─── Runner ──────────────────────────────────────────────────────────────────
def run_probe(sql, min_rows):
    """Execute a single probe. Returns (status, rows, elapsed_ms, error)."""
    t0 = time.time()
    try:
        df = session.sql(sql).to_pandas()
        elapsed = round((time.time() - t0) * 1000)
        rows = len(df)
        if rows >= min_rows:
            return "PASS", rows, elapsed, ""
        else:
            return "WARN", rows, elapsed, f"Expected >= {min_rows} rows, got {rows}"
    except Exception as e:
        elapsed = round((time.time() - t0) * 1000)
        return "FAIL", 0, elapsed, str(e)[:200]

def status_badge(status):
    colours = {"PASS": ("#1B5E20", "#C8E6C9"), "WARN": ("#F57F17", "#FFF9C4"), "FAIL": ("#B71C1C", "#FFCDD2")}
    icons    = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    fg, bg = colours.get(status, ("#424242", "#F5F5F5"))
    icon = icons.get(status, "❓")
    return f'<span style="background:{bg};color:{fg};padding:2px 10px;border-radius:12px;font-size:0.78rem;font-weight:700;">{icon} {status}</span>'


# ─── Run button / auto-run ────────────────────────────────────────────────────
run_now = st.button("▶  Run Health Check", type="primary", use_container_width=False)

if "probe_results" not in st.session_state:
    st.session_state.probe_results = None

if run_now or (auto_run and st.session_state.probe_results is None):
    results = []
    pages_seen = {}
    progress = st.progress(0, text="Running probes…")

    for i, (page_num, page_name, probe_name, sql, min_rows, desc) in enumerate(PROBES):
        progress.progress((i + 1) / len(PROBES), text=f"Probing: {page_name} — {probe_name}")
        status, rows, elapsed, error = run_probe(sql, min_rows)
        results.append({
            "page_num":   page_num,
            "page":       page_name,
            "probe":      probe_name,
            "desc":       desc,
            "status":     status,
            "rows":       rows,
            "elapsed_ms": elapsed,
            "error":      error,
        })

    progress.empty()
    st.session_state.probe_results = results
    st.session_state.probe_run_at = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S UTC")

# ─── Display results ─────────────────────────────────────────────────────────
if st.session_state.probe_results:
    results = st.session_state.probe_results
    run_at  = st.session_state.get("probe_run_at", "—")

    total  = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    warned = sum(1 for r in results if r["status"] == "WARN")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    pct    = round(passed * 100 / total) if total else 0
    avg_ms = round(sum(r["elapsed_ms"] for r in results) / total) if total else 0

    # KPI strip
    st.markdown("---")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Probes Run",   total)
    k2.metric("PASS",         passed,  delta=None)
    k3.metric("WARN",         warned,  delta=None)
    k4.metric("FAIL",         failed,  delta=None)
    k5.metric("Avg Response", f"{avg_ms} ms")

    overall = "PASS" if failed == 0 and warned == 0 else ("WARN" if failed == 0 else "FAIL")
    colour  = "#1B5E20" if overall == "PASS" else ("#E65100" if overall == "WARN" else "#B71C1C")
    st.markdown(
        f'<p style="font-size:1rem;color:{colour};font-weight:700;">Overall: {pct}% healthy &nbsp;|&nbsp; Last run: {run_at}</p>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # Group by page
    pages = {}
    for r in results:
        pages.setdefault(r["page"], []).append(r)

    page_labels = {
        "Home": "🏠 Home",
        "Customer 360": "👤 Customer 360",
        "Churn Risk": "⚠️ Churn Risk",
        "Sentiment": "💬 Sentiment",
        "Next Best Action": "🎯 Next Best Action",
        "AI Advisor": "🤖 AI Advisor",
        "Operations": "⚙️ Operations",
        "Documents": "📄 Documents",
        "What-If Simulator": "🔮 What-If Simulator",
        "Data Lineage": "🔗 Data Lineage",
    }

    for page_name, probes in pages.items():
        page_pass   = sum(1 for p in probes if p["status"] == "PASS")
        page_total  = len(probes)
        page_failed = sum(1 for p in probes if p["status"] == "FAIL")
        page_warned = sum(1 for p in probes if p["status"] == "WARN")

        if page_failed > 0:
            icon = "❌"
        elif page_warned > 0:
            icon = "⚠️"
        else:
            icon = "✅"

        label = page_labels.get(page_name, page_name)
        with st.expander(f"{icon} {label}  —  {page_pass}/{page_total} passing", expanded=(page_failed > 0)):
            for probe in probes:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 4])
                with col1:
                    st.markdown(f"**{probe['probe']}**")
                    st.caption(probe['desc'])
                with col2:
                    st.markdown(status_badge(probe['status']), unsafe_allow_html=True)
                with col3:
                    st.caption(f"{probe['elapsed_ms']} ms")
                    st.caption(f"{probe['rows']} rows")
                with col4:
                    if probe['error']:
                        st.error(probe['error'], icon="⛔")
                    else:
                        st.caption("—")
                st.divider()

    # ── Flat results table (download) ──────────────────────────────────────
    st.markdown("---")
    st.subheader("All Results (exportable)")
    df_out = pd.DataFrame(results)[["page", "probe", "status", "rows", "elapsed_ms", "error"]]
    df_out.columns = ["Page", "Probe", "Status", "Rows", "ms", "Error"]
    st.dataframe(df_out, use_container_width=True, hide_index=True)
    st.download_button(
        "Download CSV",
        data=df_out.to_csv(index=False),
        file_name=f"app_health_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

else:
    st.info("Click **Run Health Check** to probe all pages, or enable **Auto-run on load** in the sidebar.")
