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

if st.button("Refresh Data", type="primary"):
    st.experimental_rerun()
st.caption(f"Loaded at: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
st.markdown("---")


def safe_sql(query, error_label="data"):
    try:
        return session.sql(query).to_pandas()
    except Exception as e:
        st.warning(f"Could not load {error_label}: {e}")
        return pd.DataFrame()


# ── Section 1: Layer record counts ─────────────────────────────────────────
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
    with st.expander("Table breakdown by layer", expanded=True):
        for layer in layer_order:
            subset = counts[counts['LAYER'] == layer][['TABLE_NAME', 'ROW_COUNT']].reset_index(drop=True)
            if not subset.empty:
                st.markdown(f"**{layer}**")
                st.dataframe(subset)

st.markdown("---")

# ── Section 2: Dynamic table health (via SHOW DYNAMIC TABLES) ──────────────
st.markdown('<div class="layer-header">Dynamic Table Health</div>', unsafe_allow_html=True)
st.markdown("")

try:
    # Use .collect() to get Row objects — avoids to_pandas() column-count mismatch on SHOW results
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

        def style_refresh(v):
            v = str(v).upper()
            if v == 'INCREMENTAL': return 'background-color:#C8E6C9;color:#1B5E20;font-weight:bold'
            if v == 'FULL':        return 'background-color:#FFE0B2;color:#E65100'
            return ''

        def style_state(v):
            v = str(v).upper()
            if v in ('ACTIVE', 'RUNNING'): return 'background-color:#C8E6C9;color:#1B5E20'
            if v == 'SUSPENDED':           return 'background-color:#FFCDD2;color:#B71C1C'
            return ''

        styled = dt.style.map(style_refresh, subset=['REFRESH_MODE']).map(style_state, subset=['STATE'])
        st.dataframe(styled)

        mc = dt['REFRESH_MODE'].str.upper().value_counts()
        c1, c2, c3 = st.columns(3)
        c1.metric("Incremental tables", int(mc.get('INCREMENTAL', 0)), help="Only process changed rows")
        c2.metric("Full refresh tables", int(mc.get('FULL', 0)), help="Re-scan all rows every refresh")
        c3.metric("Total dynamic tables", len(dt))
except Exception as e:
    st.error(f"Could not load dynamic table info: {e}")

st.markdown("---")

# ── Section 3: Daily task run history ──────────────────────────────────────
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
    st.info("No task runs in the last 7 days. The task runs at midnight UTC. "
            "Run `python scripts/deploy_daily_pipeline.py --test` to trigger a manual batch.")
else:
    total  = len(task_hist)
    ok     = int((task_hist['STATE'] == 'SUCCEEDED').sum())
    fail   = int((task_hist['STATE'] == 'FAILED').sum())
    avg_d  = task_hist['DURATION_SEC'].mean()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Runs (7d)", total)
    k2.metric("Succeeded", ok)
    k3.metric("Failed", fail, delta=f"-{fail}" if fail else None, delta_color="inverse")
    k4.metric("Avg Duration", f"{avg_d:.0f}s" if pd.notna(avg_d) else "—")

    def style_task_state(v):
        if str(v) == 'SUCCEEDED': return 'background-color:#C8E6C9;color:#1B5E20;font-weight:bold'
        if str(v) == 'FAILED':    return 'background-color:#FFCDD2;color:#B71C1C;font-weight:bold'
        if str(v) == 'RUNNING':   return 'background-color:#E3F2FD;color:#0D47A1'
        return ''

    st.dataframe(task_hist.style.map(style_task_state, subset=['STATE']),
                 use_container_width=True)

st.markdown("---")

# ── Section 4: Dynamic table refresh history ──────────────────────────────
st.markdown('<div class="layer-header">Dynamic Table Refresh History (Last 24h)</div>', unsafe_allow_html=True)
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
    st.info("No refresh history in the last 24 hours yet.")
else:
    def style_dt_state(v):
        if str(v) == 'SUCCEEDED': return 'background-color:#C8E6C9;color:#1B5E20'
        if str(v) == 'FAILED':    return 'background-color:#FFCDD2;color:#B71C1C;font-weight:bold'
        if str(v) == 'RUNNING':   return 'background-color:#E3F2FD;color:#0D47A1'
        return ''

    st.dataframe(dt_hist.style.map(style_dt_state, subset=['STATE']),
                 use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Pipeline Info**")
st.sidebar.caption("Task: TASK_DAILY_RAW_INGEST")
st.sidebar.caption("Schedule: daily 00:00 UTC")
st.sidebar.caption("Batch: 20 customers/run")
