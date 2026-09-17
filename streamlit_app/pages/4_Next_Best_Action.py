import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Next Best Action", page_icon="🎯", layout="wide")

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

st.title("Next Best Action Recommendations")
st.caption("AI-generated action recommendations for customer retention and engagement")


def safe_sql(query, error_label="data"):
    try:
        return session.sql(query).to_pandas()
    except Exception as e:
        st.error(f"Could not load {error_label}: {e}")
        return None


# Load action types from DB (controlled values)
action_types_df = safe_sql("""
    SELECT DISTINCT ACTION_TYPE FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
    WHERE ACTION_TYPE IS NOT NULL ORDER BY 1
""", "action types")
if action_types_df is None:
    st.stop()
all_types = action_types_df["ACTION_TYPE"].tolist()

# Valid allowlists from static definitions
VALID_PRIORITIES = {"High", "Medium", "Low"}
VALID_TYPES = set(all_types)

with st.sidebar:
    st.header("Filters")
    priorities = st.multiselect("Priority", ["High", "Medium", "Low"], default=["High", "Medium"])
    selected_types = st.multiselect("Action Type", all_types, default=all_types)

# Guard empty selections
if not priorities:
    st.warning("Please select at least one priority.")
    st.stop()
if not selected_types:
    st.warning("Please select at least one action type.")
    st.stop()

# Allowlist validation -- only DB-sourced or static values pass through
safe_priorities = [p for p in priorities if p in VALID_PRIORITIES]
safe_types = [t for t in selected_types if t in VALID_TYPES]

if not safe_priorities or not safe_types:
    st.warning("No valid filter values selected.")
    st.stop()

pri_placeholders = ", ".join([f"'{p}'" for p in safe_priorities])
type_placeholders = ", ".join([f"'{t}'" for t in safe_types])

kpis = safe_sql(f"""
    SELECT COUNT(*) AS TOTAL,
           SUM(CASE WHEN PRIORITY = 'High' THEN 1 ELSE 0 END) AS HIGH_PRI,
           COUNT(DISTINCT ACTION_TYPE) AS TYPES,
           ROUND(AVG(CHURN_RISK_SCORE), 3) AS AVG_CHURN
    FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
    WHERE ACTION_TYPE IS NOT NULL
      AND PRIORITY IN ({pri_placeholders})
      AND ACTION_TYPE IN ({type_placeholders})
""", "KPIs")

if kpis is not None:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Recommendations", f"{kpis['TOTAL'].iloc[0]:,}")
    k2.metric("High Priority", f"{kpis['HIGH_PRI'].iloc[0]:,}")
    k3.metric("Distinct Action Types", f"{kpis['TYPES'].iloc[0]}")
    k4.metric("Avg Churn Risk", f"{kpis['AVG_CHURN'].iloc[0]:.3f}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Actions by Type")
    by_type = safe_sql(f"""
        SELECT ACTION_TYPE, COUNT(*) AS ACTION_COUNT
        FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
        WHERE ACTION_TYPE IS NOT NULL
          AND PRIORITY IN ({pri_placeholders}) AND ACTION_TYPE IN ({type_placeholders})
        GROUP BY 1 ORDER BY 2 DESC
    """, "actions by type")
    if by_type is not None:
        st.bar_chart(by_type, x="ACTION_TYPE", y="ACTION_COUNT")

with right:
    st.subheader("Actions by Channel")
    by_channel = safe_sql(f"""
        SELECT RECOMMENDED_CHANNEL, COUNT(*) AS ACTION_COUNT
        FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
        WHERE RECOMMENDED_CHANNEL IS NOT NULL
          AND PRIORITY IN ({pri_placeholders}) AND ACTION_TYPE IN ({type_placeholders})
        GROUP BY 1 ORDER BY 2 DESC
    """, "actions by channel")
    if by_channel is not None:
        st.bar_chart(by_channel, x="RECOMMENDED_CHANNEL", y="ACTION_COUNT")

st.divider()

st.subheader("Action Queue")
actions = safe_sql(f"""
    SELECT FULL_NAME, CUSTOMER_SEGMENT, ACTION_TYPE, ACTION_DESCRIPTION,
           PRIORITY, RECOMMENDED_CHANNEL, RATIONALE,
           ROUND(CHURN_RISK_SCORE, 3) AS CHURN_RISK,
           ROUND(LATEST_SENTIMENT_SCORE, 3) AS LAST_SENTIMENT,
           ROUND(ESTIMATED_CLV, 0) AS EST_CLV
    FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
    WHERE ACTION_TYPE IS NOT NULL
      AND PRIORITY IN ({pri_placeholders}) AND ACTION_TYPE IN ({type_placeholders})
    ORDER BY CASE PRIORITY WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
             CHURN_RISK_SCORE DESC NULLS LAST
    LIMIT 100
""", "action queue")
if actions is not None:
    st.dataframe(actions, use_container_width=True, hide_index=True)
