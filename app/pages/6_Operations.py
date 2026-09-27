import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
from utils import apply_theme, theme_sidebar, render_df

st.set_page_config(page_title="Operations & Lineage", page_icon="⚙️", layout="wide")
apply_theme()

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

st.markdown("""
<style>
.layer-header {
    background: linear-gradient(90deg, #29B5E8 0%, #11567F 100%);
    color: white; padding: 6px 14px; border-radius: 8px;
    font-size: 0.9rem; font-weight: 700; margin: 8px 0 6px 0;
    display: inline-block;
}
</style>
""", unsafe_allow_html=True)

st.title("Operations & Data Lineage")
st.caption("Pipeline health, record counts, refresh status, governance and data lineage across all layers")

col_refresh, col_ts = st.columns([1, 5])
with col_refresh:
    if st.button("Refresh Data", type="primary"):
        st.cache_data.clear()
        st.rerun()
with col_ts:
    st.caption(f"Loaded at: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

st.markdown("---")


@st.cache_data(ttl=300, show_spinner=False)
def safe_sql(query, error_label="data"):
    try:
        return session.sql(query).to_pandas()
    except Exception as e:
        st.warning(f"Could not load {error_label}: {e}")
        return pd.DataFrame()


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Pipeline Health",
    "🔗 Data Lineage",
    "🛡️ Governance",
    "🤖 AI Quality",
    "🔔 Alerts",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Pipeline Health
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    # ── Section 1: Layer record counts ────────────────────────────────────────
    st.markdown('<div class="layer-header">Record Counts by Layer</div>', unsafe_allow_html=True)
    st.markdown("")

    counts = safe_sql("""
        SELECT TABLE_SCHEMA AS LAYER, TABLE_NAME, ROW_COUNT
        FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA IN ('RAW','CLEAN','CURATED','AI','APP')
          AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY
            CASE TABLE_SCHEMA WHEN 'RAW' THEN 1 WHEN 'CLEAN' THEN 2
                WHEN 'CURATED' THEN 3 WHEN 'AI' THEN 4 ELSE 5 END,
            TABLE_NAME
    """, "record counts")

    if not counts.empty:
        layer_order = ['RAW', 'CLEAN', 'CURATED', 'AI', 'APP']
        layer_totals = counts.groupby('LAYER')['ROW_COUNT'].sum()
        layer_styles = {
            'RAW':     ('#E3F2FD', '#1565C0'),
            'CLEAN':   ('#E8F5E9', '#1B5E20'),
            'CURATED': ('#FFF8E1', '#F57F17'),
            'AI':      ('#F3E5F5', '#6A1B9A'),
            'APP':     ('#FCE4EC', '#880E4F'),
        }
        cols = st.columns(len(layer_order))
        for i, layer in enumerate(layer_order):
            total = int(layer_totals.get(layer, 0))
            bg, fg = layer_styles.get(layer, ('#F5F5F5', '#333'))
            cols[i].markdown(
                f'<div style="background:{bg};border-radius:10px;padding:14px 16px;'
                f'border-left:4px solid {fg};text-align:center">'
                f'<div style="font-size:0.7rem;font-weight:700;color:{fg};'
                f'text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px">{layer}</div>'
                f'<div style="font-size:1.8rem;font-weight:800;color:{fg}">{total:,}</div>'
                f'<div style="font-size:0.72rem;color:{fg};opacity:.7">total rows</div>'
                f'</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("Table breakdown by layer", expanded=False):
            for layer in layer_order:
                subset = counts[counts['LAYER'] == layer][['TABLE_NAME', 'ROW_COUNT']].reset_index(drop=True)
                if not subset.empty:
                    st.markdown(f"**{layer}**")
                    st.dataframe(subset, use_container_width=True)

    st.markdown("---")

    # ── Section 2: Dynamic table health ───────────────────────────────────────
    st.markdown('<div class="layer-header">Dynamic Table Health</div>', unsafe_allow_html=True)
    st.markdown("")

    try:
        rows = session.sql("SHOW DYNAMIC TABLES IN DATABASE CUSTOMER_360").collect()
        records = []
        for row in rows:
            try:
                schema = str(row['schema_name'])
                if schema not in ('CLEAN', 'CURATED', 'AI'):
                    continue
                records.append({
                    'LAYER':        schema,
                    'TABLE':        str(row['name']),
                    'ROWS':         row['rows'],
                    'LAST_REFRESH': row['data_timestamp'],
                    'REFRESH_MODE': str(row['refresh_mode']),
                    'STATE':        str(row['scheduling_state']),
                    'TARGET_LAG':   str(row['target_lag']),
                })
            except Exception:
                pass

        if not records:
            st.info("No dynamic tables found.")
        else:
            dt = pd.DataFrame(records).sort_values(['LAYER', 'TABLE'])
            render_df(dt)

            mc = dt['REFRESH_MODE'].str.upper().value_counts()
            c1, c2, c3 = st.columns(3)
            c1.metric("Incremental tables",  int(mc.get('INCREMENTAL', 0)))
            c2.metric("Full refresh tables", int(mc.get('FULL', 0)))
            c3.metric("Total dynamic tables", len(dt))
    except Exception as e:
        st.error(f"Could not load dynamic table info: {e}")

    st.markdown("---")

    # ── Section 3: Daily task run history ─────────────────────────────────────
    st.markdown('<div class="layer-header">Daily Ingestion Task — Last 7 Days</div>', unsafe_allow_html=True)
    st.markdown("")

    task_hist = safe_sql("""
        SELECT
            STATE,
            SCHEDULED_TIME,
            COMPLETED_TIME,
            DATEDIFF('second', SCHEDULED_TIME, COMPLETED_TIME) AS DURATION_SEC,
            ERROR_CODE,
            ERROR_MESSAGE
        FROM TABLE(SNOWFLAKE.INFORMATION_SCHEMA.TASK_HISTORY(
            TASK_NAME => 'TASK_DAILY_RAW_INGEST',
            SCHEDULED_TIME_RANGE_START => DATEADD('day', -7, CURRENT_TIMESTAMP()),
            RESULT_LIMIT => 50
        ))
        WHERE DATABASE_NAME = 'CUSTOMER_360' AND SCHEMA_NAME = 'RAW'
          AND SCHEDULED_TIME <= CURRENT_TIMESTAMP()
        ORDER BY SCHEDULED_TIME DESC
    """, "task history")

    if task_hist.empty:
        st.info("No task runs in the last 7 days. The task runs every 6 hours. "
                "Run `python scripts/deploy_daily_pipeline.py --test` to trigger manually.")
    else:
        total = len(task_hist)
        ok    = int((task_hist['STATE'] == 'SUCCEEDED').sum())
        fail  = int((task_hist['STATE'] == 'FAILED').sum())
        avg_d = task_hist['DURATION_SEC'].mean()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Runs (7d)", total)
        k2.metric("Succeeded", ok)
        k3.metric("Failed", fail, delta=f"-{fail}" if fail else None, delta_color="inverse")
        k4.metric("Avg Duration", f"{avg_d:.0f}s" if pd.notna(avg_d) else "—")

        render_df(task_hist)

    st.markdown("---")

    # ── Section 4: DT refresh history ─────────────────────────────────────────
    st.markdown('<div class="layer-header">Dynamic Table Refresh History — Last 24h</div>', unsafe_allow_html=True)
    st.markdown("")

    dt_hist = safe_sql("""
        SELECT
            NAME AS TABLE_NAME,
            SCHEMA_NAME AS LAYER,
            STATE,
            REFRESH_START_TIME,
            REFRESH_END_TIME,
            DATEDIFF('second', REFRESH_START_TIME, REFRESH_END_TIME) AS DURATION_SEC
        FROM TABLE(CUSTOMER_360.INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
            NAME_PREFIX => 'CUSTOMER_360.'
        ))
        WHERE REFRESH_START_TIME >= DATEADD('hour', -24, CURRENT_TIMESTAMP())
          AND SCHEMA_NAME IN ('CLEAN','CURATED','AI')
        ORDER BY REFRESH_END_TIME DESC
        LIMIT 100
    """, "DT refresh history")

    if dt_hist.empty:
        st.info("No refresh history in the last 24 hours.")
    else:
        render_df(dt_hist)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Data Lineage
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Pipeline Architecture")
    st.caption("End-to-end data flow: RAW → CLEAN → CURATED → AI → APP")
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

    st.markdown("---")
    st.subheader("Object Inventory")

    inventory = safe_sql("""
        SELECT TABLE_SCHEMA AS LAYER, TABLE_NAME, TABLE_TYPE,
               ROW_COUNT, BYTES
        FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA IN ('RAW','CLEAN','CURATED','AI','APP')
        ORDER BY
            CASE TABLE_SCHEMA WHEN 'RAW' THEN 1 WHEN 'CLEAN' THEN 2
                WHEN 'CURATED' THEN 3 WHEN 'AI' THEN 4 ELSE 5 END,
            TABLE_NAME
    """, "object inventory")

    if not inventory.empty:
        for layer in ['RAW', 'CLEAN', 'CURATED', 'AI', 'APP']:
            subset = inventory[inventory['LAYER'] == layer].reset_index(drop=True)
            if not subset.empty:
                total_rows  = int(subset['ROW_COUNT'].fillna(0).sum())
                total_bytes = int(subset['BYTES'].fillna(0).sum())
                size_mb = round(total_bytes / 1_048_576, 2)
                with st.expander(
                    f"**{layer}** — {len(subset)} objects, {total_rows:,} rows, {size_mb} MB",
                    expanded=(layer == 'AI'),
                ):
                    st.dataframe(subset[['TABLE_NAME', 'TABLE_TYPE', 'ROW_COUNT', 'BYTES']],
                                 use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Governance
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Governance Coverage")

    # ── Masking Policies ────────────────────────────────────────────────────
    try:
        mp_rows = session.sql("SHOW MASKING POLICIES IN DATABASE CUSTOMER_360").collect()
        mp_records = []
        for row in mp_rows:
            try:
                mp_records.append({
                    "POLICY_NAME":   str(row["name"]),
                    "SCHEMA":        str(row["schema_name"]),
                    "CREATED_ON":    row["created_on"],
                })
            except Exception:
                pass
        g1, g2 = st.columns(2)
        g1.metric("Masking Policies", len(mp_records))

        st.markdown("---")
        st.subheader("Masking Policy Details")
        if mp_records:
            render_df(pd.DataFrame(mp_records))
        else:
            st.info("No masking policies found in CUSTOMER_360.")
    except Exception as e:
        st.error(f"Could not load masking policies: {e}")

    # ── Row Access Policies ─────────────────────────────────────────────────
    try:
        rap_rows = session.sql("SHOW ROW ACCESS POLICIES IN DATABASE CUSTOMER_360").collect()
        rap_records = []
        for row in rap_rows:
            try:
                rap_records.append({
                    "POLICY_NAME":   str(row["name"]),
                    "SCHEMA":        str(row["schema_name"]),
                    "CREATED_ON":    row["created_on"],
                })
            except Exception:
                pass
        # fill second metric now we have the count
        try:
            g2.metric("Row Access Policies", len(rap_records))
        except Exception:
            pass

        st.markdown("---")
        st.subheader("Row Access Policies")
        if rap_records:
            render_df(pd.DataFrame(rap_records))
        else:
            st.info("No row access policies found in CUSTOMER_360.")
    except Exception as e:
        st.error(f"Could not load row access policies: {e}")

    # ── PII Tags ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("PII Tag Coverage")
    try:
        tag_rows = session.sql("SHOW TAGS IN DATABASE CUSTOMER_360").collect()
        pii_records = []
        for row in tag_rows:
            try:
                name = str(row["name"])
                if "PII" in name.upper() or "DATA_DOMAIN" in name.upper():
                    pii_records.append({
                        "TAG_NAME":   name,
                        "SCHEMA":     str(row["schema_name"]),
                        "CREATED_ON": row["created_on"],
                    })
            except Exception:
                pass
        if pii_records:
            render_df(pd.DataFrame(pii_records))
        else:
            st.info("No PII or DATA_DOMAIN tags found.")
    except Exception as e:
        st.error(f"Could not load tags: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AI Quality
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("AI Model Quality Dashboard")
    st.caption("Parse success rates and null scores from all AI dynamic tables")

    ai_quality = safe_sql("SELECT * FROM CUSTOMER_360.APP.AI_QUALITY_DASHBOARD", "AI quality")
    if not ai_quality.empty:
        render_df(ai_quality)
    else:
        st.info("AI quality dashboard has no data yet.")

    st.markdown("---")
    st.subheader("Raw AI Quality Log (Latest 50)")

    ai_log = safe_sql("""
        SELECT *
        FROM CUSTOMER_360.APP.AI_QUALITY_LOG
        ORDER BY CHECKED_AT DESC
        LIMIT 50
    """, "AI quality log")

    if not ai_log.empty:
        render_df(ai_log)
    else:
        st.info("No AI quality log entries yet.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Alerts
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Configured Alerts")
    st.caption("Proactive alerts scheduled on Snowflake — email triggered on condition breach")

    st.markdown("""
| Alert | Schedule | Condition |
|---|---|---|
| `ALERT_HIGH_CHURN_RISK` | Every 60 min | Customers with churn score ≥ 0.8 |
| `ALERT_AI_QUALITY_DEGRADATION` | Every 6 hours | LLM parse failure rate > 5% |
| `ALERT_VIP_COMPLAINT` | Every 30 min | VIP / Premium customers with 3+ complaints |
""")

    st.markdown("---")
    st.subheader("Alert Status (Live)")

    try:
        alert_rows = session.sql("SHOW ALERTS IN DATABASE CUSTOMER_360").collect()
        alert_records = []
        for row in alert_rows:
            try:
                alert_records.append({
                    'NAME':      str(row['name']),
                    'SCHEMA':    str(row['database_name']) + '.' + str(row['schema_name']),
                    'SCHEDULE':  str(row['schedule']),
                    'STATE':     str(row['state']),
                    'CONDITION': str(row['condition'])[:120],
                })
            except Exception:
                pass
        if alert_records:
            render_df(pd.DataFrame(alert_records))
        else:
            st.info("No alerts found in CUSTOMER_360 database.")
    except Exception as e:
        st.warning(f"Could not load alert status: {e}")

    st.markdown("---")
    st.subheader("Current High-Churn Customers (top 10)")

    churn_alert = safe_sql("""
        SELECT FULL_NAME, CUSTOMER_SEGMENT, ROUND(CHURN_RISK_SCORE, 3) AS CHURN_RISK_SCORE, RETENTION_URGENCY
        FROM CUSTOMER_360.AI.DT_CHURN_RISK
        WHERE CHURN_RISK_SCORE >= 0.8
        ORDER BY CHURN_RISK_SCORE DESC
        LIMIT 10
    """, "high-churn customers")

    if not churn_alert.empty:
        render_df(churn_alert)
    else:
        st.success("No customers currently above 0.8 churn threshold.")


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    theme_sidebar()
    st.divider()
    st.markdown("**Pipeline Info**")
    st.caption("Task: TASK_DAILY_RAW_INGEST")
    st.caption("Schedule: every 6 hours")
    st.caption("Batch: 20 customers/run")
