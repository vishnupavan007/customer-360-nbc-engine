import streamlit as st
import pandas as pd

st.set_page_config(page_title="Health Check", layout="wide")
st.title("App Health Check")
st.caption("Comprehensive test suite: SiS APIs, data queries, page logic, widget patterns, and AI functions")

results = []

def test(name, fn):
    try:
        r = fn()
        detail = str(r)[:120] if r is not None else ""
        results.append({"Test": name, "Status": "PASS", "Detail": detail})
    except Exception as e:
        results.append({"Test": name, "Status": "FAIL", "Detail": str(e)[:200]})

# ==========================================================================
# SECTION 1: Streamlit Runtime Info
# ==========================================================================
results.append({"Test": "Streamlit Version", "Status": st.__version__, "Detail": ""})
try:
    import sys
    results.append({"Test": "Python Version", "Status": sys.version.split()[0], "Detail": ""})
except Exception:
    results.append({"Test": "Python Version", "Status": "unknown", "Detail": ""})

# ==========================================================================
# SECTION 2: Streamlit APIs used by this app
# ==========================================================================
test("st.expander", lambda: st.expander("_hc_exp"))

with st.expander("Widget Tests (collapsed to reduce visual noise)", expanded=False):

    test("st.columns(4)", lambda: st.columns(4))
    test("st.markdown(html)", lambda: st.markdown("<b>ok</b>", unsafe_allow_html=True))
    test("st.caption", lambda: st.caption("ok"))
    test("st.markdown('---')", lambda: st.markdown("---"))
    test("st.subheader", lambda: st.subheader("_hc_sub"))

    test("st.text_input", lambda: st.text_input("_ti", key="_hc_ti"))
    test("st.radio (horizontal)", lambda: st.radio("_r", ["a","b"], key="_hc_r", horizontal=True))
    test("st.button", lambda: st.button("_b", key="_hc_b"))
    test("st.button(type=primary)", lambda: st.button("_bp", key="_hc_bp", type="primary"))
    test("st.selectbox", lambda: st.selectbox("_sb", ["a","b"], key="_hc_sb"))
    test("st.multiselect", lambda: st.multiselect("_ms", ["a","b"], key="_hc_ms"))
    test("st.slider(float)", lambda: st.slider("_sl", 0.0, 1.0, 0.5, key="_hc_sl"))
    test("st.slider(int)", lambda: st.slider("_sli", 0, 100, 50, key="_hc_sli"))

    df_test = pd.DataFrame({"A": [1,2], "B": [3,4], "C": ["x","y"]})
    test("st.dataframe(basic)", lambda: st.dataframe(df_test))
    test("st.dataframe(use_container_width)", lambda: st.dataframe(df_test, use_container_width=True))
    test("st.bar_chart", lambda: st.bar_chart(df_test.set_index("A")[["B"]]))

    test("st.session_state read/write", lambda: st.session_state.update({"_hc_state": 1}) or st.session_state["_hc_state"])

    test("st.sidebar.header", lambda: st.sidebar.header("_hc_sidebar"))
    test("st.sidebar.markdown", lambda: st.sidebar.markdown("ok"))
    test("st.sidebar.caption", lambda: st.sidebar.caption("ok"))
    test("st.sidebar.button", lambda: st.sidebar.button("_sb_btn", key="_hc_sb_btn"))

    test("styled dataframe", lambda: st.dataframe(df_test.style.highlight_max(axis=0)))

    test("st.success", lambda: st.success("ok"))
    test("st.error", lambda: st.error("ok"))
    test("st.warning", lambda: st.warning("ok"))
    test("st.info", lambda: st.info("ok"))
    test("st.spinner", lambda: None)

    test("hasattr(st, 'experimental_rerun')",
         lambda: "PASS" if hasattr(st, "experimental_rerun") else (_ for _ in ()).throw(AttributeError("missing")))
    test("hasattr(st, 'stop')",
         lambda: "PASS" if hasattr(st, "stop") else (_ for _ in ()).throw(AttributeError("missing")))

# ==========================================================================
# SECTION 3: Snowpark Session
# ==========================================================================
session = None
try:
    from snowflake.snowpark.context import get_active_session
    session = get_active_session()
    session.sql("SELECT 1 AS OK").collect()
    results.append({"Test": "Snowpark get_active_session()", "Status": "PASS", "Detail": ""})
except Exception as e:
    results.append({"Test": "Snowpark get_active_session()", "Status": "FAIL", "Detail": str(e)[:200]})

def run_query(sql):
    return session.sql(sql).to_pandas()

# ==========================================================================
# SECTION 4: Data Layer (every table the app reads)
# ==========================================================================
tables = {
    "CURATED.CUSTOMER_360_UNIFIED": "SELECT COUNT(*) AS N FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED",
    "AI.DT_CHURN_RISK": "SELECT COUNT(*) AS N FROM CUSTOMER_360.AI.DT_CHURN_RISK",
    "AI.DT_NEXT_BEST_ACTION": "SELECT COUNT(*) AS N FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION",
    "AI.DT_TRANSCRIPT_SENTIMENT": "SELECT COUNT(*) AS N FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT",
    "CURATED.CUSTOMER_INTERACTION_TIMELINE": "SELECT COUNT(*) AS N FROM CUSTOMER_360.CURATED.CUSTOMER_INTERACTION_TIMELINE",
    "CLEAN.DT_CLAIMS": "SELECT COUNT(*) AS N FROM CUSTOMER_360.CLEAN.DT_CLAIMS",
    "CLEAN.DT_LOANS": "SELECT COUNT(*) AS N FROM CUSTOMER_360.CLEAN.DT_LOANS",
    "CLEAN.DT_INTERACTIONS": "SELECT COUNT(*) AS N FROM CUSTOMER_360.CLEAN.DT_INTERACTIONS",
    "CLEAN.DT_CALL_TRANSCRIPTS": "SELECT COUNT(*) AS N FROM CUSTOMER_360.CLEAN.DT_CALL_TRANSCRIPTS",
    "CLEAN.DT_POLICIES": "SELECT COUNT(*) AS N FROM CUSTOMER_360.CLEAN.DT_POLICIES",
    "CLEAN.DT_CUSTOMERS": "SELECT COUNT(*) AS N FROM CUSTOMER_360.CLEAN.DT_CUSTOMERS",
    "INFO_SCHEMA (Operations)": "SELECT COUNT(*) AS N FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA IN ('RAW','CLEAN','CURATED','AI','APP') AND TABLE_TYPE='BASE TABLE'",
}
if session:
    for tbl, sql in tables.items():
        try:
            row = run_query(sql)
            n = int(row["N"].iloc[0])
            results.append({"Test": f"Table: {tbl}", "Status": "PASS" if n > 0 else "WARN (0 rows)", "Detail": f"{n:,} rows"})
        except Exception as e:
            results.append({"Test": f"Table: {tbl}", "Status": "FAIL", "Detail": str(e)[:150]})

# ==========================================================================
# SECTION 5: Page-specific queries (exact SQL each page runs)
# ==========================================================================
if session:
    # Home page
    test("Home: Churn Risk by Segment join", lambda: run_query(
        "SELECT c.CUSTOMER_SEGMENT, ROUND(AVG(cr.CHURN_RISK_SCORE),3) AS AVG "
        "FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c "
        "JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID=cr.CUSTOMER_ID "
        "WHERE cr.CHURN_RISK_SCORE IS NOT NULL GROUP BY c.CUSTOMER_SEGMENT"))
    test("Home: Sentiment Distribution", lambda: run_query(
        "SELECT SENTIMENT_LABEL, COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT GROUP BY SENTIMENT_LABEL"))
    test("Home: Top Action Items", lambda: run_query(
        "SELECT FULL_NAME, ACTION_TYPE, PRIORITY FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION "
        "WHERE PRIORITY='High' AND ACTION_TYPE IS NOT NULL ORDER BY CHURN_RISK_SCORE DESC LIMIT 15"))

    # Customer 360 page
    test("Cust360: Search ILIKE 'smith'", lambda: run_query(
        "SELECT CUSTOMER_ID, FULL_NAME, CUSTOMER_SEGMENT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED WHERE FULL_NAME ILIKE '%smith%' LIMIT 5"))
    test("Cust360: Search by ID", lambda: run_query(
        "SELECT CUSTOMER_ID, FULL_NAME FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED "
        "WHERE CUSTOMER_ID = (SELECT MIN(CUSTOMER_ID) FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED)"))
    test("Cust360: Customer+Churn+NBA join", lambda: run_query(
        "SELECT c.CUSTOMER_ID, cr.CHURN_RISK_SCORE, nba.ACTION_TYPE "
        "FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c "
        "LEFT JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID=cr.CUSTOMER_ID "
        "LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba ON c.CUSTOMER_ID=nba.CUSTOMER_ID LIMIT 1"))
    test("Cust360: Claims detail", lambda: run_query("SELECT CLAIM_ID, CLAIM_TYPE, CLAIM_STATUS FROM CUSTOMER_360.CLEAN.DT_CLAIMS LIMIT 3"))
    test("Cust360: Loans detail", lambda: run_query("SELECT LOAN_ID, LOAN_TYPE, LOAN_STATUS FROM CUSTOMER_360.CLEAN.DT_LOANS LIMIT 3"))
    test("Cust360: Timeline events", lambda: run_query("SELECT EVENT_DATE, EVENT_CATEGORY, EVENT_DESCRIPTION FROM CUSTOMER_360.CURATED.CUSTOMER_INTERACTION_TIMELINE LIMIT 3"))
    test("Cust360: Segment overview", lambda: run_query("SELECT CUSTOMER_SEGMENT, COUNT(*) AS CNT FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED GROUP BY CUSTOMER_SEGMENT"))

    # Churn Risk page
    test("Churn: Segment filter values", lambda: run_query("SELECT DISTINCT CUSTOMER_SEGMENT FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE IS NOT NULL"))
    test("Churn: Filtered by segment+slider", lambda: run_query(
        "SELECT FULL_NAME, CHURN_RISK_SCORE, RETENTION_URGENCY FROM CUSTOMER_360.AI.DT_CHURN_RISK "
        "WHERE CUSTOMER_SEGMENT='Premium' AND CHURN_RISK_SCORE >= 0.0 ORDER BY CHURN_RISK_SCORE DESC LIMIT 5"))
    test("Churn: Risk distribution buckets", lambda: run_query(
        "SELECT CASE WHEN CHURN_RISK_SCORE>=0.8 THEN 'Critical' WHEN CHURN_RISK_SCORE>=0.6 THEN 'High' "
        "WHEN CHURN_RISK_SCORE>=0.4 THEN 'Medium' WHEN CHURN_RISK_SCORE>=0.2 THEN 'Low' ELSE 'Minimal' END AS BUCKET, "
        "COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE IS NOT NULL GROUP BY 1"))

    # Sentiment page
    test("Sentiment: By call reason", lambda: run_query(
        "SELECT CALL_REASON, SENTIMENT_LABEL, COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT GROUP BY CALL_REASON, SENTIMENT_LABEL LIMIT 10"))
    test("Sentiment: Negative calls", lambda: run_query(
        "SELECT TRANSCRIPT_ID, CUSTOMER_ID, CALL_REASON, SENTIMENT_SCORE FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT WHERE SENTIMENT_LABEL='Negative' LIMIT 5"))
    test("Sentiment: Transcript text", lambda: run_query(
        "SELECT TRANSCRIPT_ID, LEFT(TRANSCRIPT_TEXT, 100) AS PREVIEW FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT LIMIT 1"))

    # Next Best Action page
    test("NBA: Priority filter values", lambda: run_query("SELECT DISTINCT PRIORITY FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE PRIORITY IS NOT NULL"))
    test("NBA: Action type filter values", lambda: run_query("SELECT DISTINCT ACTION_TYPE FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE ACTION_TYPE IS NOT NULL"))
    test("NBA: Filtered action queue", lambda: run_query(
        "SELECT FULL_NAME, ACTION_TYPE, PRIORITY, RECOMMENDED_CHANNEL FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION "
        "WHERE PRIORITY='High' AND ACTION_TYPE='Retention_Offer' LIMIT 5"))
    test("NBA: Actions by channel", lambda: run_query(
        "SELECT RECOMMENDED_CHANNEL, COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE ACTION_TYPE IS NOT NULL GROUP BY RECOMMENDED_CHANNEL"))

    # AI Advisor fallback queries
    test("Advisor: Top churn risk", lambda: run_query(
        "SELECT cr.FULL_NAME, ROUND(cr.CHURN_RISK_SCORE,3) AS RISK, nba.ACTION_TYPE "
        "FROM CUSTOMER_360.AI.DT_CHURN_RISK cr LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba ON cr.CUSTOMER_ID=nba.CUSTOMER_ID "
        "WHERE cr.CHURN_RISK_SCORE IS NOT NULL ORDER BY cr.CHURN_RISK_SCORE DESC LIMIT 10"))
    test("Advisor: Sentiment by segment", lambda: run_query(
        "SELECT c.CUSTOMER_SEGMENT, ROUND(AVG(s.SENTIMENT_SCORE),3) AS AVG_S "
        "FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c "
        "JOIN CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT s ON c.CUSTOMER_ID=s.CUSTOMER_ID GROUP BY c.CUSTOMER_SEGMENT"))
    test("Advisor: Complaint details", lambda: run_query(
        "SELECT c.FULL_NAME, c.COMPLAINT_COUNT, i.CHANNEL, i.SUBJECT "
        "FROM CUSTOMER_360.CLEAN.DT_INTERACTIONS i "
        "JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c ON i.CUSTOMER_ID=c.CUSTOMER_ID "
        "WHERE i.INTERACTION_TYPE='Complaint' AND c.COMPLAINT_COUNT>2 LIMIT 5"))
    test("Advisor: NBA for negative sentiment", lambda: run_query(
        "SELECT ACTION_TYPE, COUNT(*) AS CNT FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION "
        "WHERE LATEST_SENTIMENT_LABEL='Negative' AND ACTION_TYPE IS NOT NULL GROUP BY ACTION_TYPE"))
    test("Advisor: Open claims + high churn", lambda: run_query(
        "SELECT cr.FULL_NAME, cr.CHURN_RISK_SCORE, u.OPEN_CLAIMS "
        "FROM CUSTOMER_360.AI.DT_CHURN_RISK cr "
        "JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED u ON cr.CUSTOMER_ID=u.CUSTOMER_ID "
        "WHERE u.OPEN_CLAIMS>0 AND cr.CHURN_RISK_SCORE>=0.6 LIMIT 5"))
    test("Advisor: Premium high-risk count", lambda: run_query(
        "SELECT COUNT(*) AS N FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE>=0.7 AND CUSTOMER_SEGMENT='Premium'"))

    # Operations page
    test("Ops: SHOW DT via collect()", lambda: session.sql("SHOW DYNAMIC TABLES IN DATABASE CUSTOMER_360").collect())
    test("Ops: DT refresh history", lambda: run_query(
        "SELECT NAME, STATE, REFRESH_START_TIME FROM TABLE(CUSTOMER_360.INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY("
        "NAME_PREFIX=>'CUSTOMER_360.')) WHERE REFRESH_START_TIME >= DATEADD('hour',-24,CURRENT_TIMESTAMP()) "
        "AND SCHEMA_NAME IN ('CLEAN','CURATED','AI') LIMIT 5"))

    # AI Functions
    test("Cortex: SENTIMENT function", lambda: run_query("SELECT SNOWFLAKE.CORTEX.SENTIMENT('This is great') AS S"))
    test("Cortex: COMPLETE (llama3.1-8b)", lambda: run_query("SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b','Reply: ok') AS R"))

    # Data Quality
    test("DQ: Churn scores in [0,1]", lambda: run_query("SELECT COUNT(*) AS N FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE < 0 OR CHURN_RISK_SCORE > 1"))
    test("DQ: Sentiment scores in [-1,1]", lambda: run_query("SELECT COUNT(*) AS N FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT WHERE SENTIMENT_SCORE < -1 OR SENTIMENT_SCORE > 1"))
    test("DQ: Churn completeness", lambda: run_query("SELECT ROUND(COUNT(CHURN_RISK_SCORE)*100.0/NULLIF(COUNT(*),0),1) AS PCT FROM CUSTOMER_360.AI.DT_CHURN_RISK"))
    test("DQ: NBA completeness", lambda: run_query("SELECT ROUND(COUNT(ACTION_TYPE)*100.0/NULLIF(COUNT(*),0),1) AS PCT FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION"))

# ==========================================================================
# RESULTS DISPLAY
# ==========================================================================
st.markdown("---")
st.subheader("Results")

rdf = pd.DataFrame(results)
pass_count = len(rdf[rdf["Status"] == "PASS"])
fail_count = len(rdf[rdf["Status"] == "FAIL"])
warn_count = len(rdf[rdf["Status"].str.startswith("WARN")])
total = len(rdf) - 2

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Tests", total)
c2.metric("Passed", pass_count)
c3.metric("Warnings", warn_count)
c4.metric("Failed", fail_count)
c5.metric("Streamlit", st.__version__)

if fail_count == 0:
    st.success(f"All {pass_count} checks passed. The app is fully functional on this SiS runtime.")
else:
    st.error(f"{fail_count} check(s) failed. See details below.")

def color_status(val):
    if val == "PASS": return "background-color: #C8E6C9; color: #1B5E20; font-weight: bold"
    elif val == "FAIL": return "background-color: #FFCDD2; color: #B71C1C; font-weight: bold"
    elif str(val).startswith("WARN"): return "background-color: #FFE0B2; color: #E65100"
    return ""

st.dataframe(rdf.style.map(color_status, subset=["Status"]), use_container_width=True)
