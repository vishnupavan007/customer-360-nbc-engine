import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Document AI", layout="wide")

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

st.title("Document Intelligence")
st.caption("AI-powered structured extraction from insurance claim forms and policy documents using Cortex AI (llama3.1-8b)")

def run_query(sql):
    return session.sql(sql).to_pandas()

# -- KPIs --
st.markdown("---")
try:
    counts = run_query("""
        SELECT
            COUNT(*) AS TOTAL_DOCS,
            SUM(CASE WHEN DOCUMENT_TYPE = 'Claim Form' THEN 1 ELSE 0 END) AS CLAIM_FORMS,
            SUM(CASE WHEN DOCUMENT_TYPE = 'Policy Summary' THEN 1 ELSE 0 END) AS POLICY_SUMMARIES
        FROM CUSTOMER_360.AI.DT_DOCUMENT_EXTRACTED
    """)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Documents", int(counts["TOTAL_DOCS"].iloc[0]))
    c2.metric("Claim Forms", int(counts["CLAIM_FORMS"].iloc[0]))
    c3.metric("Policy Summaries", int(counts["POLICY_SUMMARIES"].iloc[0]))
except Exception as e:
    st.warning(f"Document data not yet available: {e}")

st.markdown("---")

# -- Extracted Fields Table --
st.subheader("Extracted Document Fields")
st.caption("Structured data automatically extracted from unstructured documents using Cortex AI")

try:
    doc_type_filter = st.radio("Filter by type:", ["All", "Claim Form", "Policy Summary"], horizontal=True, key="_doc_type")

    filter_map = {"Claim Form": "Claim Form", "Policy Summary": "Policy Summary"}
    if doc_type_filter in filter_map:
        extracted = run_query(f"""
            SELECT
                FILE_NAME,
                DOCUMENT_TYPE,
                REFERENCE_NUMBER,
                POLICY_NUMBER,
                CUSTOMER_NAME,
                CUSTOMER_ID,
                AMOUNT,
                CATEGORY,
                STATUS,
                DOCUMENT_DATE
            FROM CUSTOMER_360.AI.DT_DOCUMENT_EXTRACTED
            WHERE DOCUMENT_TYPE = '{filter_map[doc_type_filter]}'
            ORDER BY FILE_NAME
        """)
    else:
        extracted = run_query("""
            SELECT
                FILE_NAME,
                DOCUMENT_TYPE,
                REFERENCE_NUMBER,
                POLICY_NUMBER,
                CUSTOMER_NAME,
                CUSTOMER_ID,
                AMOUNT,
                CATEGORY,
                STATUS,
                DOCUMENT_DATE
            FROM CUSTOMER_360.AI.DT_DOCUMENT_EXTRACTED
            ORDER BY FILE_NAME
        """)
    st.dataframe(extracted, use_container_width=True)
except Exception as e:
    st.error(f"Could not load extracted data: {e}")

st.markdown("---")

# -- Document Viewer --
st.subheader("Document Viewer")
st.caption("Full document text from the RAW document store")

try:
    docs = run_query("SELECT FILE_NAME FROM CUSTOMER_360.AI.DT_DOCUMENT_PARSED ORDER BY FILE_NAME")
    if not docs.empty:
        selected = st.selectbox("Select document:", docs["FILE_NAME"].tolist(), key="_doc_select")
        if selected:
            content = run_query(f"""
                SELECT PARSED_TEXT, DOCUMENT_TYPE, FILE_SIZE_BYTES
                FROM CUSTOMER_360.AI.DT_DOCUMENT_PARSED
                WHERE FILE_NAME = '{selected}'
            """)
            if not content.empty:
                mc1, mc2 = st.columns(2)
                mc1.metric("Type", content["DOCUMENT_TYPE"].iloc[0])
                mc2.metric("Size", f"{int(content['FILE_SIZE_BYTES'].iloc[0]):,} bytes")
                st.text(content["PARSED_TEXT"].iloc[0])
except Exception as e:
    st.error(f"Could not load document viewer: {e}")

st.markdown("---")

# -- Cross-reference with Customer 360 --
st.subheader("Document-Customer Cross Reference")
st.caption("Links document customer IDs to the Customer 360 unified profile and churn risk")

try:
    xref = run_query("""
        SELECT
            d.FILE_NAME,
            d.DOCUMENT_TYPE,
            d.REFERENCE_NUMBER,
            d.CUSTOMER_NAME AS DOC_CUSTOMER_NAME,
            d.SOURCE_CUSTOMER_ID,
            d.AMOUNT,
            c.FULL_NAME AS C360_NAME,
            c.CUSTOMER_SEGMENT,
            c.IS_ACTIVE,
            ROUND(cr.CHURN_RISK_SCORE, 3) AS CHURN_RISK
        FROM CUSTOMER_360.AI.DT_DOCUMENT_EXTRACTED d
        LEFT JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
            ON d.SOURCE_CUSTOMER_ID = c.CUSTOMER_ID
        LEFT JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr
            ON d.SOURCE_CUSTOMER_ID = cr.CUSTOMER_ID
        ORDER BY d.FILE_NAME
    """)
    st.dataframe(xref, use_container_width=True)

    matched = xref["C360_NAME"].notna().sum()
    total = len(xref)
    st.caption(f"{matched} of {total} documents matched to Customer 360 profiles")
except Exception as e:
    st.info(f"Cross-reference not available: {e}")
