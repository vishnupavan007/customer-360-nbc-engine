import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd

st.set_page_config(page_title="Operations Dashboard", page_icon="⚙️", layout="wide")

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

st.markdown("""
<style>
.badge { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:700; }
.badge-incremental { background:#C8E6C9; color:#1B5E20; }
.badge-full        { background:#FFE0B2; color:#E65100; }
.badge-active      { background:#C8E6C9; color:#1B5E20; }
.badge-suspended   { background:#FFCDD2; color:#B71C1C; }
.badge-succeeded   { background:#C8E6C9; color:#1B5E20; }
.badge-failed      { background:#FFCDD2; color:#B71C1C; }
.badge-running     { background:#E3F2FD; color:#0D47A1; }
.layer-header {
    background: linear-gradient(90deg, #29B5E8 0%, #11567F 100%);
    color: white; padding: 6px 14px; border-radius: 8px;
    font-size: 0.9rem; font-weight: 700; margin: 8px 0 6px 0;
    display: inline-block;
}
</style>
""", unsafe_allow_html=True)

st.title("Operations Dashboard")
st.caption("Pipeline health, record counts, and refresh status across all layers")


def safe_sql(query, error_label="data"):
    try:
        return session.sql(query).to_pandas()
    except Exception as e:
        st.error(f"Could not load {error_label}: {e}")
        return pd.DataFrame()


# ── Refresh button ──────────────────────────────────────────────────────────
if st.button("Refresh", type="primary"):
    st.rerun()
st.caption(f"Last loaded: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.divider()

# ── Section 1: Layer record counts ─────────────────────────────────────────
st.markdown('<div class="layer-header">Record Counts by Layer</div>', unsafe_allow_html=True)

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
    layer_totals = counts.groupby('LAYER')['ROW_COUNT'].sum().reindex(layer_order).fillna(0)

    cols = st.columns(len(layer_order))
    layer_colors = {
        'RAW':     ('#E3F2FD', '#1565C0'),
        'CLEAN':   ('#E8F5E9', '#1B5E20'),
        'CURATED': ('#FFF8E1', '#F57F17'),
        'AI':      ('#F3E5F5', '#6A1B9A'),
        'APP':     ('#FCE4EC', '#880E4F'),
    }
    for i, layer in enumerate(layer_order):
        total = int(layer_totals.get(layer, 0))
        bg, fg = layer_colors.get(layer, ('#F5F5F5', '#333'))
        cols[i].markdown(
            f'<div style="background:{bg};border-radius:10px;padding:14px 16px;'
            f'border-left:4px solid {fg};text-align:center">'
            f'<div style="font-size:0.7rem;font-weight:700;color:{fg};text-transform:uppercase;'
            f'letter-spacing:.06em;margin-bottom:4px">{layer}</div>'
            f'<div style="font-size:1.8rem;font-weight:800;color:{fg}">{total:,}</div>'
            f'<div style="font-size:0.72rem;color:{fg};opacity:.7">total rows</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Detailed table breakdown
    with st.expander("Full table breakdown", expanded=True):
        pivot = counts.pivot_table(
            index='TABLE_NAME', columns='LAYER', values='ROW_COUNT', aggfunc='sum'
        ).reindex(columns=[l for l in layer_order if l in counts['LAYER'].unique()])
        pivot = pivot.fillna(0).astype(int)
        pivot.index.name = 'Table'
        st.dataframe(pivot, use_container_width=True)

st.divider()

# ── Section 2: Dynamic table health ────────────────────────────────────────
st.markdown('<div class="layer-header">Dynamic Table Health</div>', unsafe_allow_html=True)

dt = safe_sql("""
    SELECT
        SCHEMA_NAME AS LAYER,
        NAME AS TABLE_NAME,
        ROWS AS ROW_COUNT,
        DATA_TIMESTAMP AS LAST_REFRESH,
        REFRESH_MODE,
        SCHEDULING_STATE,
        TARGET_LAG
    FROM TABLE(CUSTOMER_360.INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY())
    WHERE DATABASE_NAME = 'CUSTOMER_360'
      AND SCHEMA_NAME IN ('CLEAN','CURATED','AI')
    ORDER BY
        CASE SCHEMA_NAME WHEN 'CLEAN' THEN 1 WHEN 'CURATED' THEN 2 ELSE 3 END,
        NAME
""", "dynamic tables")

if dt.empty:
    # Fallback: SHOW DYNAMIC TABLES parsed from session
    dt_raw = safe_sql("""
        SELECT SCHEMA_NAME, TABLE_NAME, ROW_COUNT,
               NULL AS LAST_REFRESH, NULL AS REFRESH_MODE,
               NULL AS SCHEDULING_STATE, NULL AS TARGET_LAG
        FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA IN ('CLEAN','CURATED','AI')
          AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """, "table fallback")
    dt = dt_raw.rename(columns={
        'SCHEMA_NAME':'LAYER','TABLE_NAME':'TABLE_NAME',
        'ROW_COUNT':'ROW_COUNT'
    }) if not dt_raw.empty else pd.DataFrame()

if not dt.empty:
    def style_refresh(v):
        if str(v).upper() == 'INCREMENTAL': return 'background-color:#C8E6C9;color:#1B5E20;font-weight:bold'
        if str(v).upper() == 'FULL': return 'background-color:#FFE0B2;color:#E65100'
        return ''

    def style_state(v):
        if str(v).upper() in ('ACTIVE','RUNNING'): return 'background-color:#C8E6C9;color:#1B5E20'
        if str(v).upper() == 'SUSPENDED': return 'background-color:#FFCDD2;color:#B71C1C'
        return ''

    display_cols = [c for c in ['LAYER','TABLE_NAME','ROW_COUNT','LAST_REFRESH',
                                'REFRESH_MODE','SCHEDULING_STATE','TARGET_LAG'] if c in dt.columns]
    styled = dt[display_cols].style
    if 'REFRESH_MODE' in dt.columns:
        styled = styled.map(style_refresh, subset=['REFRESH_MODE'])
    if 'SCHEDULING_STATE' in dt.columns:
        styled = styled.map(style_state, subset=['SCHEDULING_STATE'])

    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Refresh mode summary
    if 'REFRESH_MODE' in dt.columns:
        mode_counts = dt['REFRESH_MODE'].value_counts()
        c1, c2 = st.columns(2)
        inc = int(mode_counts.get('INCREMENTAL', 0))
        full = int(mode_counts.get('FULL', 0))
        c1.metric("Incremental tables", inc, help="Only process changed rows — efficient")
        c2.metric("Full refresh tables", full, help="Re-scan all rows every refresh — higher cost")

st.divider()

# ── Section 3: Daily task run history ──────────────────────────────────────
st.markdown('<div class="layer-header">Daily Ingestion Task History</div>', unsafe_allow_html=True)

task_hist = safe_sql("""
    SELECT
        NAME AS TASK,
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
    st.info("No task runs recorded yet. The task is scheduled for midnight UTC — check back after the first run.")
    st.caption("Manual test: run `python scripts/deploy_daily_pipeline.py --test` to trigger a batch.")
else:
    # Summary KPIs
    total_runs = len(task_hist)
    succeeded  = int((task_hist['STATE'] == 'SUCCEEDED').sum())
    failed     = int((task_hist['STATE'] == 'FAILED').sum())
    avg_dur    = task_hist['DURATION_SEC'].mean()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Runs (7d)", total_runs)
    k2.metric("Succeeded", succeeded)
    k3.metric("Failed", failed, delta=f"-{failed}" if failed else None, delta_color="inverse")
    k4.metric("Avg Duration", f"{avg_dur:.0f}s" if pd.notna(avg_dur) else "—")

    def style_state_task(v):
        if str(v) == 'SUCCEEDED': return 'background-color:#C8E6C9;color:#1B5E20;font-weight:bold'
        if str(v) == 'FAILED':    return 'background-color:#FFCDD2;color:#B71C1C;font-weight:bold'
        if str(v) == 'RUNNING':   return 'background-color:#E3F2FD;color:#0D47A1'
        return ''

    styled_task = task_hist.style.map(style_state_task, subset=['STATE'])
    st.dataframe(styled_task, use_container_width=True, hide_index=True)

st.divider()

# ── Section 4: Dynamic table refresh history ──────────────────────────────
st.markdown('<div class="layer-header">Dynamic Table Refresh History (Last 24h)</div>', unsafe_allow_html=True)

dt_hist = safe_sql("""
    SELECT
        NAME AS TABLE_NAME,
        SCHEMA_NAME AS LAYER,
        STATE,
        REFRESH_START_TIME,
        REFRESH_END_TIME,
        DATEDIFF('second', REFRESH_START_TIME, REFRESH_END_TIME) AS DURATION_SEC,
        ROWS_INSERTED,
        ROWS_DELETED,
        ERROR_CODE,
        ERROR_MESSAGE
    FROM TABLE(CUSTOMER_360.INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
        NAME_PREFIX => 'CUSTOMER_360.'
    ))
    WHERE REFRESH_START_TIME >= DATEADD('hour', -24, CURRENT_TIMESTAMP())
    ORDER BY REFRESH_END_TIME DESC
    LIMIT 100
""", "DT refresh history")

if dt_hist.empty:
    st.info("No refresh history in the last 24 hours, or history is not yet available.")
else:
    def style_dt_state(v):
        if str(v) == 'SUCCEEDED': return 'background-color:#C8E6C9;color:#1B5E20'
        if str(v) == 'FAILED':    return 'background-color:#FFCDD2;color:#B71C1C;font-weight:bold'
        if str(v) == 'RUNNING':   return 'background-color:#E3F2FD;color:#0D47A1'
        return ''

    display = [c for c in ['LAYER','TABLE_NAME','STATE','REFRESH_START_TIME',
                            'REFRESH_END_TIME','DURATION_SEC','ROWS_INSERTED',
                            'ROWS_DELETED','ERROR_CODE'] if c in dt_hist.columns]
    styled_dt = dt_hist[display].style.map(style_dt_state, subset=['STATE'])
    st.dataframe(styled_dt, use_container_width=True, hide_index=True)

    # Rows inserted per table chart
    if 'ROWS_INSERTED' in dt_hist.columns and dt_hist['ROWS_INSERTED'].sum() > 0:
        st.subheader("Rows Inserted per Table (Last 24h)")
        ins = (dt_hist.groupby('TABLE_NAME')['ROWS_INSERTED']
               .sum().reset_index()
               .sort_values('ROWS_INSERTED', ascending=False))
        st.bar_chart(ins, x='TABLE_NAME', y='ROWS_INSERTED', color='#29B5E8')

st.sidebar.markdown("---")
st.sidebar.markdown("**Quick Links**")
st.sidebar.caption("Task schedule: daily at 00:00 UTC")
st.sidebar.caption("Batch size: 20 customers/day")
st.sidebar.code("python scripts/deploy_daily_pipeline.py --status")
