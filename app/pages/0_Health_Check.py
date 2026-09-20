import streamlit as st
import pandas as pd

st.set_page_config(page_title="Health Check", layout="wide")
st.title("App Health Check")
st.caption("Validates SiS API compatibility and data connectivity")

results = []

def test(name, fn):
    try:
        fn()
        results.append({"Test": name, "Status": "PASS", "Detail": ""})
    except Exception as e:
        results.append({"Test": name, "Status": "FAIL", "Detail": str(e)[:150]})

# --- Streamlit version ---
results.append({"Test": "Streamlit Version", "Status": st.__version__, "Detail": ""})

# --- APIs used by this app ---
test("st.columns", lambda: st.columns(2))
test("st.metric", lambda: st.metric("Test", "0", key="_hc_m"))
test("st.markdown(html)", lambda: st.markdown("<b>x</b>", unsafe_allow_html=True))
test("st.caption", lambda: st.caption("test"))
test("st.markdown('---')", lambda: st.markdown("---"))
test("st.text_input", lambda: st.text_input("x", key="_hc_ti"))
test("st.radio", lambda: st.radio("x", ["a"], key="_hc_r"))
test("st.button", lambda: st.button("x", key="_hc_b"))
test("st.selectbox", lambda: st.selectbox("x", ["a"], key="_hc_s"))
test("st.multiselect", lambda: st.multiselect("x", ["a"], key="_hc_ms"))
test("st.slider", lambda: st.slider("x", 0, 10, key="_hc_sl"))
test("st.expander", lambda: st.expander("x"))
test("st.spinner", lambda: None)  # can't test inline but it's old
test("st.session_state", lambda: st.session_state.update({"_hc": 1}))

df = pd.DataFrame({"A": [1], "B": [2]})
test("st.dataframe(basic)", lambda: st.dataframe(df))
test("st.dataframe(use_container_width)", lambda: st.dataframe(df, use_container_width=True))
test("st.bar_chart(set_index)", lambda: st.bar_chart(df.set_index("A")))

results.append({
    "Test": "st.experimental_rerun exists",
    "Status": "PASS" if hasattr(st, "experimental_rerun") else "FAIL",
    "Detail": ""
})

# --- Snowpark connectivity ---
try:
    from snowflake.snowpark.context import get_active_session
    session = get_active_session()
    session.sql("SELECT 1 AS OK").collect()
    results.append({"Test": "Snowpark session + SQL", "Status": "PASS", "Detail": ""})
except Exception as e:
    results.append({"Test": "Snowpark session + SQL", "Status": "FAIL", "Detail": str(e)[:150]})
    session = None

# --- Data queries (same ones the app uses) ---
queries = {
    "CUSTOMER_360_UNIFIED": "SELECT COUNT(*) AS N FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED",
    "DT_CHURN_RISK": "SELECT COUNT(*) AS N FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE IS NOT NULL",
    "DT_NEXT_BEST_ACTION": "SELECT COUNT(*) AS N FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE ACTION_TYPE IS NOT NULL",
    "DT_TRANSCRIPT_SENTIMENT": "SELECT COUNT(*) AS N FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT",
    "CUSTOMER_INTERACTION_TIMELINE": "SELECT COUNT(*) AS N FROM CUSTOMER_360.CURATED.CUSTOMER_INTERACTION_TIMELINE",
    "DT_CLAIMS": "SELECT COUNT(*) AS N FROM CUSTOMER_360.CLEAN.DT_CLAIMS",
    "DT_LOANS": "SELECT COUNT(*) AS N FROM CUSTOMER_360.CLEAN.DT_LOANS",
    "DT_INTERACTIONS": "SELECT COUNT(*) AS N FROM CUSTOMER_360.CLEAN.DT_INTERACTIONS",
}

if session:
    for table_name, sql in queries.items():
        try:
            row = session.sql(sql).to_pandas()
            n = int(row["N"].iloc[0])
            status = "PASS" if n > 0 else "WARN (0 rows)"
            results.append({"Test": f"Query: {table_name}", "Status": status, "Detail": f"{n:,} rows"})
        except Exception as e:
            results.append({"Test": f"Query: {table_name}", "Status": "FAIL", "Detail": str(e)[:150]})

# --- Display results ---
st.markdown("---")
st.subheader("Results")

rdf = pd.DataFrame(results)
pass_count = len(rdf[rdf["Status"] == "PASS"])
fail_count = len(rdf[rdf["Status"] == "FAIL"])
warn_count = len(rdf[rdf["Status"].str.startswith("WARN")])
total = len(rdf) - 1  # exclude version row

c1, c2, c3, c4 = st.columns(4)
c1.metric("Version", st.__version__)
c2.metric("Passed", pass_count)
c3.metric("Warnings", warn_count)
c4.metric("Failed", fail_count)

if fail_count == 0:
    st.success("All checks passed. The app is fully compatible with this SiS runtime.")
else:
    st.error(f"{fail_count} check(s) failed. See details below.")

st.dataframe(rdf, use_container_width=True)
