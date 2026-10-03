import streamlit as st
from snowflake.snowpark.context import get_active_session
from utils import apply_theme, theme_sidebar

st.set_page_config(page_title="What-If Simulator", page_icon="🔮", layout="wide")
apply_theme()

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

with st.sidebar:
    theme_sidebar()
    st.divider()

st.title("What-If Simulator")
st.caption("Predict how changes would affect a customer's churn risk using Cortex AI")

search = st.text_input("Enter customer name or ID", placeholder="e.g. Robert Tanaka or 831530")

if search:
    search_clean = search.strip()
    if search_clean.isdigit():
        where = f"c.CUSTOMER_ID = {int(search_clean)}"
    else:
        name_safe = "".join(ch for ch in search_clean if ch.isalnum() or ch in " -.")
        where = f"LOWER(c.FULL_NAME) LIKE '%{name_safe.lower()}%'"

    customers = session.sql(f"""
        SELECT c.CUSTOMER_ID, c.FULL_NAME, c.CUSTOMER_SEGMENT,
               c.ACTIVE_POLICIES, c.LAPSED_POLICIES, c.TOTAL_PREMIUM,
               c.OPEN_CLAIMS, c.COMPLAINT_COUNT, c.MAX_DAYS_PAST_DUE,
               c.TOTAL_OUTSTANDING_BALANCE, c.DAYS_SINCE_LAST_INTERACTION,
               COALESCE(cr.CHURN_RISK_SCORE, 0.5) AS CURRENT_CHURN_RISK,
               cr.RETENTION_URGENCY,
               COALESCE(h.HEALTH_SCORE, 50) AS CURRENT_HEALTH_SCORE,
               COALESCE(h.HEALTH_GRADE, 'C') AS CURRENT_HEALTH_GRADE
        FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
        LEFT JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID = cr.CUSTOMER_ID
        LEFT JOIN CUSTOMER_360.AI.DT_CUSTOMER_HEALTH_SCORE h ON c.CUSTOMER_ID = h.CUSTOMER_ID
        WHERE {where}
        LIMIT 5
    """).to_pandas()

    if customers.empty:
        st.warning("No customers found.")
    else:
        for _, row in customers.iterrows():
            cid = int(row["CUSTOMER_ID"])
            st.subheader(f"{row['FULL_NAME']} ({row['CUSTOMER_SEGMENT']})")

            c1, c2, c3 = st.columns(3)
            c1.metric("Current Churn Risk", f"{row['CURRENT_CHURN_RISK']:.2f}")
            c2.metric("Health Score", f"{row['CURRENT_HEALTH_SCORE']:.0f}")
            c3.metric("Health Grade", row["CURRENT_HEALTH_GRADE"])

            st.markdown("---")
            st.markdown("**Adjust parameters to see predicted impact:**")

            col_l, col_r = st.columns(2)
            with col_l:
                new_premium_discount = st.slider(
                    "Premium Discount (%)", 0, 50, 0, key=f"disc_{cid}",
                    help="Simulate offering a premium discount"
                )
                resolve_claims = st.checkbox(
                    "Resolve all open claims", key=f"claims_{cid}"
                )
                add_interaction = st.checkbox(
                    "Schedule proactive outreach", key=f"outreach_{cid}"
                )
            with col_r:
                reduce_past_due = st.slider(
                    "Reduce days past due to", 0, int(max(row["MAX_DAYS_PAST_DUE"], 0)),
                    int(max(row["MAX_DAYS_PAST_DUE"], 0)), key=f"dpd_{cid}",
                    help="Simulate resolving payment delays"
                )
                resolve_complaints = st.checkbox(
                    "Resolve all complaints", key=f"comp_{cid}"
                )

            if st.button("Predict Impact", key=f"predict_{cid}", type="primary"):
                modified_premium = float(row["TOTAL_PREMIUM"]) * (1 - new_premium_discount / 100)
                modified_claims = 0 if resolve_claims else int(row["OPEN_CLAIMS"])
                modified_complaints = 0 if resolve_complaints else int(row["COMPLAINT_COUNT"])
                modified_dpd = reduce_past_due
                modified_interaction_days = 1 if add_interaction else int(row["DAYS_SINCE_LAST_INTERACTION"])

                prompt = (
                    f"You are a customer risk analyst. Given this MODIFIED customer profile, "
                    f"predict the new churn risk score (0.0 to 1.0). "
                    f"Return ONLY a valid JSON object using double quotes for all keys and string values. "
                    f"Keys: predicted_churn_risk (float), risk_change (one of: decreased, increased, unchanged), "
                    f"explanation (1-2 sentences why). Example: {{\"predicted_churn_risk\": 0.45, \"risk_change\": \"decreased\", \"explanation\": \"reason\"}}. "
                    f"Do not use single quotes. Do not include any text outside the JSON object. "
                    f"ORIGINAL: churn_risk={row['CURRENT_CHURN_RISK']:.2f}, "
                    f"segment={row['CUSTOMER_SEGMENT']}, "
                    f"premium=${row['TOTAL_PREMIUM']:.0f}, "
                    f"open_claims={row['OPEN_CLAIMS']}, "
                    f"complaints={row['COMPLAINT_COUNT']}, "
                    f"days_past_due={row['MAX_DAYS_PAST_DUE']}, "
                    f"days_since_interaction={row['DAYS_SINCE_LAST_INTERACTION']}. "
                    f"AFTER CHANGES: premium=${modified_premium:.0f} "
                    f"({new_premium_discount}% discount), "
                    f"open_claims={modified_claims}, "
                    f"complaints={modified_complaints}, "
                    f"days_past_due={modified_dpd}, "
                    f"days_since_interaction={modified_interaction_days}."
                )

                with st.spinner("Running Cortex AI prediction..."):
                    safe_prompt = prompt.replace("'", "''")
                    try:
                        result = session.sql(f"""
                            SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b', '{safe_prompt}') AS PREDICTION
                        """).collect()

                        import json, re, ast
                        raw = result[0]["PREDICTION"] if result else ""
                        match = re.search(r'\{[\s\S]*\}', raw)
                        if match:
                            json_str = match.group()
                            try:
                                pred = json.loads(json_str)
                            except json.JSONDecodeError:
                                # LLM returned single-quoted Python dict — fall back to ast
                                try:
                                    pred = ast.literal_eval(json_str)
                                except Exception:
                                    st.warning("Could not parse AI prediction. Raw response:")
                                    st.text(raw[:500])
                                    pred = None
                            if pred is not None:
                                new_risk = float(pred.get("predicted_churn_risk", row["CURRENT_CHURN_RISK"]))
                                change = pred.get("risk_change", "unchanged")
                                explanation = pred.get("explanation", "")

                                delta = new_risk - float(row["CURRENT_CHURN_RISK"])
                                delta_pct = delta * 100

                                st.markdown("### Prediction Results")
                                r1, r2, r3 = st.columns(3)
                                r1.metric("Predicted Churn Risk", f"{new_risk:.2f}",
                                         delta=f"{delta_pct:+.1f}%",
                                         delta_color="inverse")
                                r2.metric("Risk Change", change.title())
                                r3.metric("Current → Predicted",
                                         f"{row['CURRENT_CHURN_RISK']:.2f} → {new_risk:.2f}")

                                if explanation:
                                    st.info(f"**AI Analysis:** {explanation}")
                        else:
                            st.warning("Could not parse AI prediction. Raw response:")
                            st.text(raw[:500])
                    except Exception as e:
                        st.error(f"Prediction failed: {e}")
else:
    st.info("Search for a customer to start the What-If simulation.")
    st.markdown("""
    **How it works:**
    1. Search for a customer by name or ID
    2. Adjust parameters (premium discount, resolve claims, outreach, etc.)
    3. Click "Predict Impact" to see the AI-predicted churn risk change
    4. Use insights to decide which retention actions are most effective
    """)
