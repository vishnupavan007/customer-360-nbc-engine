import streamlit as st

st.set_page_config(page_title="Next Best Action", page_icon="🎯", layout="wide")
conn = st.connection("snowflake")

st.title("Next Best Action Recommendations")
st.caption("AI-generated action recommendations for customer retention and engagement")

# Filters
with st.sidebar:
    st.header("Filters")
    priorities = st.multiselect("Priority", ["High", "Medium", "Low"], default=["High", "Medium"])
    action_types_df = conn.query("""
        SELECT DISTINCT ACTION_TYPE
        FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
        WHERE ACTION_TYPE IS NOT NULL
        ORDER BY 1
    """)
    all_types = action_types_df["ACTION_TYPE"].tolist()
    selected_types = st.multiselect("Action Type", all_types, default=all_types)

pri_filter = "','".join(priorities)
type_filter = "','".join(selected_types)

# KPIs
k1, k2, k3, k4 = st.columns(4)

kpis = conn.query(f"""
    SELECT
        COUNT(*) AS TOTAL_ACTIONS,
        SUM(CASE WHEN PRIORITY = 'High' THEN 1 ELSE 0 END) AS HIGH_PRI,
        COUNT(DISTINCT ACTION_TYPE) AS DISTINCT_TYPES,
        ROUND(AVG(CHURN_RISK_SCORE), 3) AS AVG_CHURN
    FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
    WHERE ACTION_TYPE IS NOT NULL
      AND PRIORITY IN ('{pri_filter}')
      AND ACTION_TYPE IN ('{type_filter}')
""")

k1.metric("Total Recommendations", f"{kpis['TOTAL_ACTIONS'].iloc[0]:,}")
k2.metric("High Priority", f"{kpis['HIGH_PRI'].iloc[0]:,}")
k3.metric("Distinct Action Types", f"{kpis['DISTINCT_TYPES'].iloc[0]}")
k4.metric("Avg Churn Risk", f"{kpis['AVG_CHURN'].iloc[0]:.3f}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Actions by Type")
    by_type = conn.query(f"""
        SELECT ACTION_TYPE, COUNT(*) AS ACTION_COUNT
        FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
        WHERE ACTION_TYPE IS NOT NULL
          AND PRIORITY IN ('{pri_filter}')
          AND ACTION_TYPE IN ('{type_filter}')
        GROUP BY ACTION_TYPE
        ORDER BY ACTION_COUNT DESC
    """)
    st.bar_chart(by_type, x="ACTION_TYPE", y="ACTION_COUNT")

with right:
    st.subheader("Actions by Channel")
    by_channel = conn.query(f"""
        SELECT RECOMMENDED_CHANNEL, COUNT(*) AS ACTION_COUNT
        FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
        WHERE RECOMMENDED_CHANNEL IS NOT NULL
          AND PRIORITY IN ('{pri_filter}')
          AND ACTION_TYPE IN ('{type_filter}')
        GROUP BY RECOMMENDED_CHANNEL
        ORDER BY ACTION_COUNT DESC
    """)
    st.bar_chart(by_channel, x="RECOMMENDED_CHANNEL", y="ACTION_COUNT")

st.divider()

st.subheader("Action Queue")
actions = conn.query(f"""
    SELECT
        nba.FULL_NAME,
        nba.CUSTOMER_SEGMENT,
        nba.ACTION_TYPE,
        nba.ACTION_DESCRIPTION,
        nba.PRIORITY,
        nba.RECOMMENDED_CHANNEL,
        nba.RATIONALE,
        ROUND(nba.CHURN_RISK_SCORE, 3) AS CHURN_RISK,
        ROUND(nba.LATEST_SENTIMENT_SCORE, 3) AS LAST_SENTIMENT,
        ROUND(nba.ESTIMATED_CLV, 0) AS EST_CLV
    FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba
    WHERE nba.ACTION_TYPE IS NOT NULL
      AND nba.PRIORITY IN ('{pri_filter}')
      AND nba.ACTION_TYPE IN ('{type_filter}')
    ORDER BY
        CASE nba.PRIORITY WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
        nba.CHURN_RISK_SCORE DESC
    LIMIT 100
""")
st.dataframe(actions, use_container_width=True, hide_index=True)

st.divider()

st.subheader("Action Summary by Segment & Priority")
summary = conn.query(f"""
    SELECT
        CUSTOMER_SEGMENT,
        PRIORITY,
        COUNT(*) AS ACTIONS,
        ROUND(AVG(CHURN_RISK_SCORE), 3) AS AVG_CHURN,
        ROUND(AVG(ESTIMATED_CLV), 0) AS AVG_CLV
    FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
    WHERE ACTION_TYPE IS NOT NULL
      AND PRIORITY IN ('{pri_filter}')
      AND ACTION_TYPE IN ('{type_filter}')
    GROUP BY CUSTOMER_SEGMENT, PRIORITY
    ORDER BY CUSTOMER_SEGMENT, PRIORITY
""")
st.dataframe(summary, use_container_width=True, hide_index=True)
