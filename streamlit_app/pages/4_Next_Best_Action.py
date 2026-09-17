import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Next Best Action", page_icon="🎯", layout="wide")
session = get_active_session()

st.title("Next Best Action Recommendations")
st.caption("AI-generated action recommendations for customer retention and engagement")

with st.sidebar:
    st.header("Filters")
    priorities = st.multiselect("Priority", ["High", "Medium", "Low"], default=["High", "Medium"])
    action_types = session.sql("""
        SELECT DISTINCT ACTION_TYPE FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
        WHERE ACTION_TYPE IS NOT NULL ORDER BY 1
    """).to_pandas()
    all_types = action_types["ACTION_TYPE"].tolist()
    selected_types = st.multiselect("Action Type", all_types, default=all_types)

pri_filter = "','".join(priorities)
type_filter = "','".join(selected_types)

kpis = session.sql(f"""
    SELECT COUNT(*) AS TOTAL,
           SUM(CASE WHEN PRIORITY = 'High' THEN 1 ELSE 0 END) AS HIGH_PRI,
           COUNT(DISTINCT ACTION_TYPE) AS TYPES,
           ROUND(AVG(CHURN_RISK_SCORE), 3) AS AVG_CHURN
    FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
    WHERE ACTION_TYPE IS NOT NULL
      AND PRIORITY IN ('{pri_filter}')
      AND ACTION_TYPE IN ('{type_filter}')
""").to_pandas()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Recommendations", f"{kpis['TOTAL'].iloc[0]:,}")
k2.metric("High Priority", f"{kpis['HIGH_PRI'].iloc[0]:,}")
k3.metric("Distinct Action Types", f"{kpis['TYPES'].iloc[0]}")
k4.metric("Avg Churn Risk", f"{kpis['AVG_CHURN'].iloc[0]:.3f}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Actions by Type")
    by_type = session.sql(f"""
        SELECT ACTION_TYPE, COUNT(*) AS ACTION_COUNT
        FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
        WHERE ACTION_TYPE IS NOT NULL
          AND PRIORITY IN ('{pri_filter}') AND ACTION_TYPE IN ('{type_filter}')
        GROUP BY 1 ORDER BY 2 DESC
    """).to_pandas()
    st.bar_chart(by_type, x="ACTION_TYPE", y="ACTION_COUNT")

with right:
    st.subheader("Actions by Channel")
    by_channel = session.sql(f"""
        SELECT RECOMMENDED_CHANNEL, COUNT(*) AS ACTION_COUNT
        FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
        WHERE RECOMMENDED_CHANNEL IS NOT NULL
          AND PRIORITY IN ('{pri_filter}') AND ACTION_TYPE IN ('{type_filter}')
        GROUP BY 1 ORDER BY 2 DESC
    """).to_pandas()
    st.bar_chart(by_channel, x="RECOMMENDED_CHANNEL", y="ACTION_COUNT")

st.divider()

st.subheader("Action Queue")
actions = session.sql(f"""
    SELECT FULL_NAME, CUSTOMER_SEGMENT, ACTION_TYPE, ACTION_DESCRIPTION,
           PRIORITY, RECOMMENDED_CHANNEL, RATIONALE,
           ROUND(CHURN_RISK_SCORE, 3) AS CHURN_RISK,
           ROUND(LATEST_SENTIMENT_SCORE, 3) AS LAST_SENTIMENT,
           ROUND(ESTIMATED_CLV, 0) AS EST_CLV
    FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
    WHERE ACTION_TYPE IS NOT NULL
      AND PRIORITY IN ('{pri_filter}') AND ACTION_TYPE IN ('{type_filter}')
    ORDER BY CASE PRIORITY WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
             CHURN_RISK_SCORE DESC NULLS LAST
    LIMIT 100
""").to_pandas()
st.dataframe(actions, use_container_width=True, hide_index=True)
