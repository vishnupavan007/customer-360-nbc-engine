import streamlit as st
from snowflake.snowpark.context import get_active_session
from utils import apply_theme, theme_sidebar, render_df

st.set_page_config(page_title="Data Lineage", page_icon="🔗", layout="wide")
apply_theme()

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

with st.sidebar:
    theme_sidebar()

st.title("Data Lineage & Pipeline Map")
st.caption("Visualize how data flows through the medallion architecture: RAW → CLEAN → CURATED → AI → APP")


def safe_sql(query, label="data"):
    try:
        return session.sql(query).to_pandas()
    except Exception as e:
        st.error(f"Could not load {label}: {e}")
        return None


# -- Pipeline Architecture --
st.subheader("Pipeline Architecture")
st.markdown("""
```
┌─────────────────────────────────────────────────────────────────┐
│                    CUSTOMER 360 DATA PIPELINE                   │
├─────────┬───────────┬──────────┬────────────┬──────────────────┤
│   RAW   │   CLEAN   │ CURATED  │     AI     │      APP         │
│ (7 tbl) │ (6 DTs)   │ (2 DTs)  │ (5 DTs)    │ (Agent+Views)    │
├─────────┼───────────┼──────────┼────────────┼──────────────────┤
│Customers│→DT_CUST   │          │            │                  │
│Policies │→DT_POLICY ├→UNIFIED  │→CHURN_RISK │→Semantic View    │
│Claims   │→DT_CLAIMS │ (7-way   │→NBA        │→Cortex Agent     │
│Loans    │→DT_LOANS  │  JOIN)   │→SENTIMENT  │→Search Service   │
│Interact │→DT_INTER  │          │→DOC_PARSED │→Streamlit App    │
│Transcr  │→DT_TRANS  ├→TIMELINE │→DOC_EXTRACT│→Health Score     │
│Documents│           │ (6 UNION)│→HEALTH     │→Email Workflow   │
└─────────┴───────────┴──────────┴────────────┴──────────────────┘
    ↑ INSERT        DOWNSTREAM       DOWNSTREAM    60min / 5min
    every 6h        (auto)           (auto)        (scheduled)
```
""")

# -- Layer Row Counts --
st.subheader("Layer Row Counts")
layer_counts = safe_sql("""
    SELECT 'RAW' AS LAYER, TABLE_NAME, ROW_COUNT
    FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'RAW' AND TABLE_TYPE = 'BASE TABLE' AND ROW_COUNT > 0
    UNION ALL
    SELECT 'CLEAN', TABLE_NAME, ROW_COUNT
    FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'CLEAN' AND ROW_COUNT > 0
    UNION ALL
    SELECT 'CURATED', TABLE_NAME, ROW_COUNT
    FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'CURATED' AND ROW_COUNT > 0
    UNION ALL
    SELECT 'AI', TABLE_NAME, ROW_COUNT
    FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'AI' AND ROW_COUNT > 0
    ORDER BY LAYER, TABLE_NAME
""", "layer counts")
if layer_counts is not None and not layer_counts.empty:
    for layer in ['RAW', 'CLEAN', 'CURATED', 'AI']:
        subset = layer_counts[layer_counts['LAYER'] == layer]
        if not subset.empty:
            total = int(subset['ROW_COUNT'].sum())
            st.markdown(f"**{layer}** — {len(subset)} tables, {total:,} total rows")
            render_df(subset[['TABLE_NAME', 'ROW_COUNT']])

# -- Dynamic Table Dependency Chain --
st.markdown("---")
st.subheader("Dynamic Table Refresh Status")
dt_status = safe_sql("""
    SELECT
        NAME,
        SCHEMA_NAME AS SCHEMA,
        TARGET_LAG,
        REFRESH_MODE,
        SCHEDULING_STATE,
        ROWS
    FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY())
    QUALIFY ROW_NUMBER() OVER (PARTITION BY NAME ORDER BY VALID_FROM DESC) = 1
    ORDER BY SCHEMA_NAME, NAME
""", "DT status")

if dt_status is None:
    dt_status = safe_sql("""
        SELECT TABLE_NAME AS NAME, TABLE_SCHEMA AS SCHEMA, ROW_COUNT AS ROWS
        FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
          AND TABLE_SCHEMA IN ('CLEAN', 'CURATED', 'AI')
          AND TABLE_NAME LIKE 'DT_%'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """, "DT fallback")

if dt_status is not None and not dt_status.empty:
    render_df(dt_status)

# -- Governance Status --
st.markdown("---")
st.subheader("Governance Coverage")
gov = safe_sql("""
    SELECT
        (SELECT COUNT(*) FROM CUSTOMER_360.INFORMATION_SCHEMA.MASKING_POLICIES) AS MASKING_POLICIES,
        (SELECT COUNT(*) FROM CUSTOMER_360.INFORMATION_SCHEMA.ROW_ACCESS_POLICIES) AS ROW_ACCESS_POLICIES
""", "governance")
if gov is not None and not gov.empty:
    g1, g2 = st.columns(2)
    g1.metric("Masking Policies", int(gov["MASKING_POLICIES"].iloc[0]))
    g2.metric("Row Access Policies", int(gov["ROW_ACCESS_POLICIES"].iloc[0]))

# -- AI Quality --
st.markdown("---")
st.subheader("AI Model Quality")
ai_quality = safe_sql("SELECT * FROM CUSTOMER_360.APP.AI_QUALITY_DASHBOARD", "AI quality")
if ai_quality is not None and not ai_quality.empty:
    render_df(ai_quality)

# -- Active Alerts --
st.markdown("---")
st.subheader("Active Alerts")
st.markdown("""
| Alert | Schedule | Monitors |
|---|---|---|
| ALERT_HIGH_CHURN_RISK | 60 min | Customers with churn >= 0.8 |
| ALERT_AI_QUALITY_DEGRADATION | 6 hours | LLM parse failure > 5% |
| ALERT_VIP_COMPLAINT | 30 min | VIP/Premium with 3+ complaints |
""")
