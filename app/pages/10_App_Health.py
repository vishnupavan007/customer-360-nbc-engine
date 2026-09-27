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
    auto_run     = st.checkbox("Auto-run on load",      value=True)
    include_llm  = st.checkbox("Include LLM probes",    value=False,
                               help="Runs CORTEX.COMPLETE calls (slow, ~5s each)")
    st.caption("LLM probes are off by default to keep health checks fast.")

st.title("App Health Check")
st.caption("Live probe of every page's core queries — verifies data is reachable and returns expected rows")

# ─── Probe definitions ──────────────────────────────────────────────────────
# (page_num, page_name, probe_name, sql, min_rows, description, needs_llm)
PROBES = [
    # ── Home ──────────────────────────────────────────────────────────────────
    (0, "Home", "Customer count KPI",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED",
     1, "Unified customer table is readable", False),

    (0, "Home", "High churn KPI",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE >= 0.7",
     0, "Churn risk DT returns high-risk count", False),

    (0, "Home", "High priority actions KPI",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE PRIORITY = 'High'",
     0, "NBA DT returns high-priority actions", False),

    (0, "Home", "Documents processed KPI",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_DOCUMENT_EXTRACTED",
     0, "Document extracted DT is readable", False),

    # ── Page 1: Customer 360 View ─────────────────────────────────────────────
    (1, "Customer 360", "Customer search query",
     "SELECT CUSTOMER_ID, FULL_NAME, CUSTOMER_SEGMENT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED LIMIT 10",
     1, "Unified view returns customer rows", False),

    (1, "Customer 360", "Interaction timeline",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_INTERACTION_TIMELINE",
     1, "Timeline DT returns events", False),

    (1, "Customer 360", "Churn join",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_CHURN_RISK cr JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c ON cr.CUSTOMER_ID = c.CUSTOMER_ID",
     1, "Churn-to-customer join resolves", False),

    # ── Page 2: Churn Risk ────────────────────────────────────────────────────
    (2, "Churn Risk", "Segment list for filter",
     "SELECT DISTINCT CUSTOMER_SEGMENT FROM CUSTOMER_360.AI.DT_CHURN_RISK ORDER BY 1",
     1, "Segments available for sidebar filter", False),

    (2, "Churn Risk", "Urgency distribution",
     "SELECT RETENTION_URGENCY, COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_CHURN_RISK GROUP BY 1 ORDER BY 1",
     1, "Urgency breakdown query runs", False),

    (2, "Churn Risk", "Top churn customers",
     "SELECT FULL_NAME, CHURN_RISK_SCORE FROM CUSTOMER_360.AI.DT_CHURN_RISK ORDER BY CHURN_RISK_SCORE DESC LIMIT 10",
     1, "Top-N churn table renders", False),

    # ── Page 3: Sentiment Analysis ────────────────────────────────────────────
    (3, "Sentiment", "KPI aggregation",
     "SELECT COUNT(*) AS TOTAL, ROUND(AVG(SENTIMENT_SCORE),3) AS AVG_SENT, SUM(CASE WHEN SENTIMENT_LABEL='Negative' THEN 1 ELSE 0 END) AS NEG FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT",
     1, "Sentiment KPI aggregation returns a row", False),

    (3, "Sentiment", "Distribution by label",
     "SELECT SENTIMENT_LABEL, COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT GROUP BY 1",
     1, "Label breakdown query runs", False),

    (3, "Sentiment", "Weekly trend",
     "SELECT DATE_TRUNC('WEEK', CALL_DATE) AS WK, ROUND(AVG(SENTIMENT_SCORE),3) AS AVG_S FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT GROUP BY 1 ORDER BY 1 LIMIT 20",
     1, "Weekly sentiment trend query runs", False),

    # ── Page 4: Next Best Action ──────────────────────────────────────────────
    (4, "Next Best Action", "Action types for filter",
     "SELECT DISTINCT ACTION_TYPE FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE ACTION_TYPE IS NOT NULL ORDER BY 1",
     1, "Action type list available for filter", False),

    (4, "Next Best Action", "High-priority NBA rows",
     "SELECT FULL_NAME, ACTION_TYPE, PRIORITY FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE PRIORITY='High' LIMIT 20",
     1, "High-priority NBA rows render", False),

    (4, "Next Best Action", "Action mix chart",
     "SELECT ACTION_TYPE, COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION GROUP BY 1 ORDER BY CNT DESC",
     1, "Action type distribution query runs", False),

    # ── Page 5: AI Advisor ────────────────────────────────────────────────────
    (5, "AI Advisor", "Customer context data",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED WHERE COMPLAINT_COUNT > 0",
     1, "Customer complaint context is available", False),

    (5, "AI Advisor", "CORTEX.COMPLETE (LLM) probe",
     "SELECT SNOWFLAKE.CORTEX.COMPLETE('snowflake-arctic', 'Reply with the single word OK') AS REPLY",
     1, "LLM endpoint is reachable", True),

    (5, "AI Advisor", "Critical retention data",
     "SELECT FULL_NAME, RETENTION_URGENCY, CHURN_RISK_SCORE FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE RETENTION_URGENCY='Critical' LIMIT 5",
     0, "Critical retention context available", False),

    # ── Page 6: Operations ────────────────────────────────────────────────────
    (6, "Operations", "Layer row counts",
     "SELECT TABLE_SCHEMA AS LAYER, COUNT(*) AS TABLES FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA IN ('RAW','CLEAN','CURATED','AI','APP') GROUP BY 1",
     1, "Information schema layer summary runs", False),

    (6, "Operations", "Dynamic tables count",
     "SELECT COUNT(*) AS ACTIVE_DTS FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA IN ('CLEAN','CURATED','AI') AND TABLE_TYPE = 'BASE TABLE'",
     1, "Dynamic tables present in pipeline schemas", False),

    (6, "Operations", "All layers populated",
     "SELECT COUNT(*) AS POPULATED_TABLES FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA IN ('RAW','CLEAN','CURATED','AI','APP') AND ROW_COUNT > 0",
     1, "All pipeline layers have data", False),

    # ── Page 7: Document Intelligence ────────────────────────────────────────
    (7, "Documents", "Document count KPIs",
     "SELECT COUNT(*) AS TOTAL, SUM(CASE WHEN DOCUMENT_TYPE='Claim Form' THEN 1 ELSE 0 END) AS CLAIMS FROM CUSTOMER_360.AI.DT_DOCUMENT_EXTRACTED",
     1, "Document KPI aggregation runs", False),

    (7, "Documents", "Extracted fields table",
     "SELECT FILE_NAME, DOCUMENT_TYPE, REFERENCE_NUMBER, AMOUNT FROM CUSTOMER_360.AI.DT_DOCUMENT_EXTRACTED LIMIT 10",
     1, "Extracted document fields render", False),

    (7, "Documents", "Document-customer cross-ref",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED WHERE TOTAL_DOCUMENTS > 0",
     1, "Documents linked to real customers", False),

    # ── Page 8: What-If Simulator ─────────────────────────────────────────────
    (8, "What-If Simulator", "Health score DT",
     "SELECT COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_CUSTOMER_HEALTH_SCORE",
     1, "Health score DT has rows", False),

    (8, "What-If Simulator", "3-way join",
     "SELECT c.FULL_NAME, cr.CHURN_RISK_SCORE, h.HEALTH_SCORE FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c LEFT JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID=cr.CUSTOMER_ID LEFT JOIN CUSTOMER_360.AI.DT_CUSTOMER_HEALTH_SCORE h ON c.CUSTOMER_ID=h.CUSTOMER_ID LIMIT 5",
     1, "3-way join for What-If page resolves", False),

    (8, "What-If Simulator", "CORTEX.COMPLETE prediction (LLM)",
     "SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-7b', 'What is 2+2? Reply with one word.') AS REPLY",
     1, "Prediction LLM call succeeds", True),

    # ── Page 9: Data Lineage ──────────────────────────────────────────────────
    (9, "Data Lineage", "DT pipeline count",
     "SELECT COUNT(*) AS TOTAL_DTS FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA IN ('CLEAN','CURATED','AI') AND TABLE_TYPE = 'BASE TABLE'",
     1, "Dynamic tables present in pipeline schemas", False),

    (9, "Data Lineage", "Layer size totals",
     "SELECT TABLE_SCHEMA, SUM(ROW_COUNT) AS TOTAL_ROWS FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA IN ('RAW','CLEAN','CURATED','AI','APP') GROUP BY 1",
     1, "Layer row count aggregation runs", False),

    (9, "Data Lineage", "Full table inventory",
     "SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA IN ('RAW','CLEAN','CURATED','AI','APP') ORDER BY 1, 2",
     1, "Full table inventory renders", False),
]

# ─── Runner ──────────────────────────────────────────────────────────────────
def run_probe(sql, min_rows):
    """Execute a probe. Returns (status, rows, elapsed_ms, error)."""
    t0 = time.time()
    try:
        df = session.sql(sql).to_pandas()
        elapsed = round((time.time() - t0) * 1000)
        rows = len(df)
        if rows >= min_rows:
            return "PASS", rows, elapsed, ""
        return "WARN", rows, elapsed, f"Expected >= {min_rows} rows, got {rows}"
    except Exception as e:
        elapsed = round((time.time() - t0) * 1000)
        return "FAIL", 0, elapsed, str(e)[:200]

def status_badge(status):
    colours = {
        "PASS":   ("#1B5E20", "#C8E6C9"),
        "WARN":   ("#F57F17", "#FFF9C4"),
        "FAIL":   ("#B71C1C", "#FFCDD2"),
        "SKIP":   ("#424242", "#F5F5F5"),
    }
    icons = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏭️"}
    fg, bg = colours.get(status, ("#424242", "#F5F5F5"))
    icon = icons.get(status, "❓")
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 10px;'
        f'border-radius:12px;font-size:0.78rem;font-weight:700;">'
        f'{icon} {status}</span>'
    )

# ─── Trigger logic ────────────────────────────────────────────────────────────
col_btn, col_clear = st.columns([2, 8])
with col_btn:
    run_now = st.button("▶  Run Health Check", type="primary")
with col_clear:
    if st.button("Clear Results"):
        st.session_state.probe_results = None
        st.session_state.probe_run_at  = None

if "probe_results" not in st.session_state:
    st.session_state.probe_results = None
if "probe_run_at" not in st.session_state:
    st.session_state.probe_run_at = None

should_run = run_now or (auto_run and st.session_state.probe_results is None)

if should_run:
    active_probes = [p for p in PROBES if (not p[6]) or include_llm]
    results = []
    progress_bar = st.progress(0)
    status_text  = st.empty()

    for i, (page_num, page_name, probe_name, sql, min_rows, desc, needs_llm) in enumerate(active_probes):
        status_text.caption(f"Probing {page_name}: {probe_name}…")
        progress_bar.progress(int((i + 1) / len(active_probes) * 100))

        if needs_llm and not include_llm:
            result_status, rows, elapsed, error = "SKIP", 0, 0, "LLM probes disabled"
        else:
            result_status, rows, elapsed, error = run_probe(sql, min_rows)

        results.append({
            "page_num":   page_num,
            "page":       page_name,
            "probe":      probe_name,
            "desc":       desc,
            "status":     result_status,
            "rows":       rows,
            "elapsed_ms": elapsed,
            "error":      error,
        })

    progress_bar.empty()
    status_text.empty()
    st.session_state.probe_results = results
    st.session_state.probe_run_at  = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S UTC")

# ─── Display ─────────────────────────────────────────────────────────────────
if st.session_state.probe_results:
    results = st.session_state.probe_results
    run_at  = st.session_state.probe_run_at or "—"

    total  = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    warned = sum(1 for r in results if r["status"] == "WARN")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped= sum(1 for r in results if r["status"] == "SKIP")
    pct    = round(passed * 100 / (total - skipped)) if (total - skipped) > 0 else 0
    avg_ms = round(sum(r["elapsed_ms"] for r in results if r["status"] != "SKIP") /
                   max(1, total - skipped))

    st.markdown("---")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Probes",   total)
    k2.metric("PASS",     passed)
    k3.metric("WARN",     warned)
    k4.metric("FAIL",     failed)
    k5.metric("SKIP",     skipped)
    k6.metric("Avg ms",   avg_ms)

    overall = "PASS" if failed == 0 and warned == 0 else ("WARN" if failed == 0 else "FAIL")
    colour  = {"PASS": "#1B5E20", "WARN": "#E65100", "FAIL": "#B71C1C"}[overall]
    icon    = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}[overall]
    st.markdown(
        f'<p style="font-size:1.05rem;color:{colour};font-weight:700;">'
        f'{icon}&nbsp; Overall: {pct}% healthy &nbsp;|&nbsp; Last run: {run_at}</p>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # Group by page
    pages = {}
    for r in results:
        pages.setdefault(r["page"], []).append(r)

    page_labels = {
        "Home":              "🏠 Home",
        "Customer 360":      "👤 Customer 360",
        "Churn Risk":        "⚠️ Churn Risk",
        "Sentiment":         "💬 Sentiment",
        "Next Best Action":  "🎯 Next Best Action",
        "AI Advisor":        "🤖 AI Advisor",
        "Operations":        "⚙️ Operations",
        "Documents":         "📄 Documents",
        "What-If Simulator": "🔮 What-If Simulator",
        "Data Lineage":      "🔗 Data Lineage",
    }

    for page_name, probes in pages.items():
        page_pass   = sum(1 for p in probes if p["status"] == "PASS")
        page_fail   = sum(1 for p in probes if p["status"] == "FAIL")
        page_warn   = sum(1 for p in probes if p["status"] == "WARN")
        page_active = sum(1 for p in probes if p["status"] != "SKIP")

        hdr_icon = "❌" if page_fail > 0 else ("⚠️" if page_warn > 0 else "✅")
        label    = page_labels.get(page_name, page_name)

        with st.expander(
            f"{hdr_icon}  {label}  —  {page_pass}/{page_active} passing",
            expanded=(page_fail > 0),
        ):
            for probe in probes:
                c1, c2, c3, c4 = st.columns([3, 1, 1, 5])
                with c1:
                    st.markdown(f"**{probe['probe']}**")
                    st.caption(probe["desc"])
                with c2:
                    st.markdown(status_badge(probe["status"]), unsafe_allow_html=True)
                with c3:
                    if probe["status"] != "SKIP":
                        st.caption(f"{probe['elapsed_ms']} ms")
                        st.caption(f"{probe['rows']} rows")
                    else:
                        st.caption("skipped")
                with c4:
                    if probe["status"] == "FAIL":
                        st.error(probe["error"])
                    elif probe["status"] == "WARN":
                        st.warning(probe["error"])
                    elif probe["status"] == "SKIP":
                        st.caption("Enable LLM probes in sidebar to run this check.")
                    else:
                        st.caption("—")
                st.divider()

    # ── Export ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("All Results")
    df_out = pd.DataFrame(results)[["page", "probe", "status", "rows", "elapsed_ms", "error"]]
    df_out.columns = ["Page", "Probe", "Status", "Rows", "ms", "Error"]
    st.dataframe(df_out, use_container_width=True)
    csv_data = df_out.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name="app_health.csv",
        mime="text/csv",
    )

else:
    st.info(
        "Click **Run Health Check** above to probe all pages, "
        "or enable **Auto-run on load** in the sidebar."
    )
