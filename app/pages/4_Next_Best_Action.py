import streamlit as st
from snowflake.snowpark.context import get_active_session
import plotly.graph_objects as go
from utils import apply_theme, theme_sidebar, render_df

st.set_page_config(page_title="Next Best Action", page_icon="🎯", layout="wide")
apply_theme()

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()


def safe_sql(query, error_label="data"):
    try:
        return session.sql(query).to_pandas()
    except Exception as e:
        st.error(f"Could not load {error_label}: {e}")
        return None


def _hbar(df, x_col, y_col):
    dark = st.session_state.get("dark_mode", False)
    bg   = "#1c1e2e" if dark else "#FFFFFF"
    text = "#FAFAFA" if dark else "#1A237E"
    grid = "#33363d" if dark else "#E0E0E0"
    fig  = go.Figure(go.Bar(
        x=df[x_col], y=df[y_col], orientation="h",
        marker_color="#29B5E8",
        text=df[x_col], textposition="outside",
        textfont=dict(color=text, size=11),
    ))
    fig.update_layout(
        paper_bgcolor=bg, plot_bgcolor=bg,
        font=dict(color=text, size=11),
        margin=dict(l=10, r=40, t=20, b=10),
        height=max(180, len(df) * 44),
        xaxis=dict(showgrid=True, gridcolor=grid, zeroline=False, color=text),
        yaxis=dict(showgrid=False, color=text, automargin=True),
    )
    st.plotly_chart(fig, use_container_width=True)


# Load action types before sidebar (needed for filter)
action_types_df = safe_sql("""
    SELECT DISTINCT ACTION_TYPE FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
    WHERE ACTION_TYPE IS NOT NULL ORDER BY 1
""", "action types")
if action_types_df is None:
    st.stop()
all_types = action_types_df["ACTION_TYPE"].tolist()

VALID_PRIORITIES = {"High", "Medium", "Low"}
VALID_TYPES      = set(all_types)

with st.sidebar:
    theme_sidebar()
    st.divider()
    st.header("Filters")
    priorities     = st.multiselect("Priority", ["High", "Medium", "Low"], default=["High", "Medium"])
    selected_types = st.multiselect("Action Type", all_types, default=all_types)

st.title("Next Best Action Recommendations")
st.caption("AI-generated action recommendations for customer retention and engagement")

if not priorities:
    st.warning("Please select at least one priority.")
    st.stop()
if not selected_types:
    st.warning("Please select at least one action type.")
    st.stop()

safe_priorities = [p for p in priorities if p in VALID_PRIORITIES]
safe_types      = [t for t in selected_types if t in VALID_TYPES]
if not safe_priorities or not safe_types:
    st.warning("No valid filter values selected.")
    st.stop()

pri_sql  = ", ".join(f"'{p}'" for p in safe_priorities)
type_sql = ", ".join(f"'{t}'" for t in safe_types)

kpis = safe_sql(f"""
    SELECT COUNT(*) AS TOTAL,
           SUM(CASE WHEN PRIORITY = 'High' THEN 1 ELSE 0 END) AS HIGH_PRI,
           COUNT(DISTINCT ACTION_TYPE) AS TYPES,
           ROUND(AVG(CHURN_RISK_SCORE), 3) AS AVG_CHURN
    FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
    WHERE ACTION_TYPE IS NOT NULL
      AND PRIORITY IN ({pri_sql}) AND ACTION_TYPE IN ({type_sql})
""", "KPIs")

if kpis is not None:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Recommendations", f"{kpis['TOTAL'].iloc[0]:,}")
    k2.metric("High Priority",         f"{kpis['HIGH_PRI'].iloc[0]:,}")
    k3.metric("Distinct Action Types", f"{kpis['TYPES'].iloc[0]}")
    k4.metric("Avg Churn Risk",        f"{kpis['AVG_CHURN'].iloc[0]:.3f}")

st.markdown("---")
left, right = st.columns(2)

with left:
    st.subheader("Actions by Type")
    by_type = safe_sql(f"""
        SELECT ACTION_TYPE, COUNT(*) AS ACTION_COUNT
        FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
        WHERE ACTION_TYPE IS NOT NULL
          AND PRIORITY IN ({pri_sql}) AND ACTION_TYPE IN ({type_sql})
        GROUP BY 1 ORDER BY 2 DESC
    """, "actions by type")
    if by_type is not None:
        _hbar(by_type, "ACTION_COUNT", "ACTION_TYPE")

with right:
    st.subheader("Actions by Channel")
    by_channel = safe_sql(f"""
        SELECT RECOMMENDED_CHANNEL, COUNT(*) AS ACTION_COUNT
        FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
        WHERE RECOMMENDED_CHANNEL IS NOT NULL
          AND PRIORITY IN ({pri_sql}) AND ACTION_TYPE IN ({type_sql})
        GROUP BY 1 ORDER BY 2 DESC
    """, "actions by channel")
    if by_channel is not None:
        _hbar(by_channel, "ACTION_COUNT", "RECOMMENDED_CHANNEL")

st.markdown("---")
st.subheader("Action Queue")
actions = safe_sql(f"""
    SELECT FULL_NAME, CUSTOMER_SEGMENT, ACTION_TYPE, ACTION_DESCRIPTION,
           PRIORITY, RECOMMENDED_CHANNEL,
           ROUND(CHURN_RISK_SCORE, 3) AS CHURN_RISK
    FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
    WHERE ACTION_TYPE IS NOT NULL
      AND PRIORITY IN ({pri_sql}) AND ACTION_TYPE IN ({type_sql})
    ORDER BY CASE PRIORITY WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
             CHURN_RISK_SCORE DESC NULLS LAST
    LIMIT 100
""", "action queue")

if actions is not None:
    def _pri_style(v):
        return {"High":"font-weight:700;color:#EF5350",
                "Medium":"color:#FFA726","Low":"color:#66BB6A"}.get(str(v),"")
    def _risk_style(v):
        try:
            f = float(v)
            if f >= 0.8: return "font-weight:700;color:#EF5350"
            if f >= 0.6: return "color:#FFA726"
            if f >= 0.4: return "color:#FFEE58"
            return "color:#66BB6A"
        except: return ""
    render_df(actions, col_styles={"PRIORITY": _pri_style, "CHURN_RISK": _risk_style})
