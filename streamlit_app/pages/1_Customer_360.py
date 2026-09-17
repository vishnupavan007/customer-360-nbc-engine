import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Customer 360 View", page_icon="👤", layout="wide")

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

st.title("Customer 360 View")
st.caption("Search and explore unified customer profiles")

search_term = st.text_input("Search by customer name or ID", placeholder="e.g. James Smith or 42")

# Allowlist for segments (sourced from DB, not user input)
VALID_SEGMENTS = {"Basic", "Standard", "Premium", "VIP"}


def safe_sql(query, error_label="data"):
    """Execute SQL and return DataFrame; show error and stop on failure."""
    try:
        return session.sql(query).to_pandas()
    except Exception as e:
        st.error(f"Could not load {error_label}: {e}")
        return None


if search_term:
    search_stripped = search_term.strip()
    if search_stripped.isdigit():
        # Numeric ID -- safe integer cast
        customers = safe_sql(
            f"SELECT c.CUSTOMER_ID, c.FULL_NAME, c.EMAIL, c.PHONE, c.CUSTOMER_SEGMENT,"
            f" c.CITY, c.STATE, c.COUNTRY, c.AGE, c.CREDIT_SCORE, c.ANNUAL_INCOME,"
            f" c.IS_ACTIVE, c.TENURE_MONTHS, c.TOTAL_POLICIES, c.ACTIVE_POLICIES,"
            f" c.TOTAL_PREMIUM, c.TOTAL_CLAIMS, c.OPEN_CLAIMS, c.TOTAL_LOANS,"
            f" c.TOTAL_OUTSTANDING_BALANCE, c.MAX_DAYS_PAST_DUE, c.COMPLAINT_COUNT,"
            f" c.TOTAL_CALLS, c.COMPOSITE_RISK_LEVEL, ROUND(c.ESTIMATED_CLV, 0) AS ESTIMATED_CLV"
            f" FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c"
            f" WHERE c.CUSTOMER_ID = {int(search_stripped)} LIMIT 20",
            "customer search"
        )
    else:
        # Name search -- use parameterized query to prevent SQL injection
        customers = safe_sql(
            f"SELECT c.CUSTOMER_ID, c.FULL_NAME, c.EMAIL, c.PHONE, c.CUSTOMER_SEGMENT,"
            f" c.CITY, c.STATE, c.COUNTRY, c.AGE, c.CREDIT_SCORE, c.ANNUAL_INCOME,"
            f" c.IS_ACTIVE, c.TENURE_MONTHS, c.TOTAL_POLICIES, c.ACTIVE_POLICIES,"
            f" c.TOTAL_PREMIUM, c.TOTAL_CLAIMS, c.OPEN_CLAIMS, c.TOTAL_LOANS,"
            f" c.TOTAL_OUTSTANDING_BALANCE, c.MAX_DAYS_PAST_DUE, c.COMPLAINT_COUNT,"
            f" c.TOTAL_CALLS, c.COMPOSITE_RISK_LEVEL, ROUND(c.ESTIMATED_CLV, 0) AS ESTIMATED_CLV"
            f" FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c"
            f" WHERE LOWER(c.FULL_NAME) LIKE '%' || LOWER(:1) || '%' LIMIT 20",
            "customer search"
        )
        if customers is None:
            # Snowpark named binding not always available -- fallback with sanitized input
            name_safe = "".join(c for c in search_stripped if c.isalnum() or c in " -.'")
            customers = safe_sql(
                f"SELECT c.CUSTOMER_ID, c.FULL_NAME, c.EMAIL, c.PHONE, c.CUSTOMER_SEGMENT,"
                f" c.CITY, c.STATE, c.COUNTRY, c.AGE, c.CREDIT_SCORE, c.ANNUAL_INCOME,"
                f" c.IS_ACTIVE, c.TENURE_MONTHS, c.TOTAL_POLICIES, c.ACTIVE_POLICIES,"
                f" c.TOTAL_PREMIUM, c.TOTAL_CLAIMS, c.OPEN_CLAIMS, c.TOTAL_LOANS,"
                f" c.TOTAL_OUTSTANDING_BALANCE, c.MAX_DAYS_PAST_DUE, c.COMPLAINT_COUNT,"
                f" c.TOTAL_CALLS, c.COMPOSITE_RISK_LEVEL, ROUND(c.ESTIMATED_CLV, 0) AS ESTIMATED_CLV"
                f" FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c"
                f" WHERE LOWER(c.FULL_NAME) LIKE '%{name_safe.lower()}%' LIMIT 20",
                "customer search"
            )

    if customers is None or customers.empty:
        st.warning("No customers found.")
    else:
        for _, row in customers.iterrows():
            cid = int(row["CUSTOMER_ID"])
            with st.expander(f"{row['FULL_NAME']} (ID: {cid}) — {row['CUSTOMER_SEGMENT']}", expanded=len(customers) == 1):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Credit Score", row["CREDIT_SCORE"])
                c2.metric("Annual Income", f"${row['ANNUAL_INCOME']:,.0f}")
                c3.metric("Est. CLV", f"${row['ESTIMATED_CLV']:,.0f}")
                c4.metric("Risk Level", row["COMPOSITE_RISK_LEVEL"])

                tab1, tab2, tab3, tab4 = st.tabs(["Profile", "Policies & Claims", "Loans", "Interactions"])

                with tab1:
                    p1, p2 = st.columns(2)
                    with p1:
                        st.markdown(f"- **Email**: {row['EMAIL']}\n- **Phone**: {row['PHONE']}\n- **Location**: {row['CITY']}, {row['STATE']}, {row['COUNTRY']}")
                    with p2:
                        st.markdown(f"- **Age**: {row['AGE']}\n- **Tenure**: {row['TENURE_MONTHS']} months\n- **Active**: {'Yes' if row['IS_ACTIVE'] else 'No'}")

                with tab2:
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Total Policies", int(row["TOTAL_POLICIES"]))
                    m2.metric("Active Policies", int(row["ACTIVE_POLICIES"]))
                    m3.metric("Total Premium", f"${row['TOTAL_PREMIUM']:,.0f}")
                    m4.metric("Open Claims", int(row["OPEN_CLAIMS"]))
                    claims = safe_sql(
                        f"SELECT CLAIM_ID, CLAIM_TYPE, CLAIM_STATUS, CLAIM_AMOUNT, FILED_DATE"
                        f" FROM CUSTOMER_360.CLEAN.DT_CLAIMS"
                        f" WHERE CUSTOMER_ID = {cid} ORDER BY FILED_DATE DESC LIMIT 10",
                        "claims"
                    )
                    if claims is not None and not claims.empty:
                        st.dataframe(claims, use_container_width=True, hide_index=True)

                with tab3:
                    l1, l2, l3 = st.columns(3)
                    l1.metric("Total Loans", int(row["TOTAL_LOANS"]))
                    l2.metric("Outstanding Balance", f"${row['TOTAL_OUTSTANDING_BALANCE']:,.0f}")
                    l3.metric("Max Days Past Due", int(row["MAX_DAYS_PAST_DUE"]))
                    loans = safe_sql(
                        f"SELECT LOAN_TYPE, LOAN_STATUS, PRINCIPAL_AMOUNT,"
                        f" OUTSTANDING_BALANCE, DAYS_PAST_DUE, DELINQUENCY_CATEGORY"
                        f" FROM CUSTOMER_360.CLEAN.DT_LOANS"
                        f" WHERE CUSTOMER_ID = {cid} ORDER BY ORIGINATION_DATE DESC LIMIT 10",
                        "loans"
                    )
                    if loans is not None and not loans.empty:
                        st.dataframe(loans, use_container_width=True, hide_index=True)

                with tab4:
                    timeline = safe_sql(
                        f"SELECT EVENT_DATE, EVENT_CATEGORY, EVENT_DESCRIPTION, EVENT_STATUS"
                        f" FROM CUSTOMER_360.CURATED.CUSTOMER_INTERACTION_TIMELINE"
                        f" WHERE CUSTOMER_ID = {cid} ORDER BY EVENT_DATE DESC LIMIT 20",
                        "timeline"
                    )
                    if timeline is not None and not timeline.empty:
                        st.dataframe(timeline, use_container_width=True, hide_index=True)

                churn_nba = safe_sql(
                    f"SELECT cr.CHURN_RISK_SCORE, cr.RETENTION_URGENCY, cr.MODEL_CONFIDENCE,"
                    f" nba.ACTION_TYPE, nba.ACTION_DESCRIPTION, nba.PRIORITY,"
                    f" nba.RECOMMENDED_CHANNEL, nba.RATIONALE"
                    f" FROM CUSTOMER_360.AI.DT_CHURN_RISK cr"
                    f" LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba ON cr.CUSTOMER_ID = nba.CUSTOMER_ID"
                    f" WHERE cr.CUSTOMER_ID = {cid}",
                    "AI insights"
                )
                if churn_nba is not None and not churn_nba.empty:
                    st.subheader("AI Insights")
                    ai1, ai2, ai3 = st.columns(3)
                    ai1.metric("Churn Risk", f"{(churn_nba['CHURN_RISK_SCORE'].iloc[0] or 0):.2f}")
                    ai2.metric("Urgency", churn_nba["RETENTION_URGENCY"].iloc[0] or "N/A")
                    ai3.metric("Confidence", f"{(churn_nba['MODEL_CONFIDENCE'].iloc[0] or 0):.0%}")
                    if churn_nba["ACTION_TYPE"].iloc[0]:
                        st.info(f"**Action ({churn_nba['PRIORITY'].iloc[0]})**: {churn_nba['ACTION_DESCRIPTION'].iloc[0]}\n\n**Channel**: {churn_nba['RECOMMENDED_CHANNEL'].iloc[0]} | **Why**: {churn_nba['RATIONALE'].iloc[0]}")
else:
    st.info("Enter a customer name or ID to search.")
    seg = safe_sql("""
        SELECT CUSTOMER_SEGMENT, COUNT(*) AS CUSTOMERS,
               SUM(CASE WHEN IS_ACTIVE THEN 1 ELSE 0 END) AS ACTIVE,
               ROUND(AVG(CREDIT_SCORE), 0) AS AVG_CREDIT_SCORE,
               ROUND(AVG(TOTAL_PREMIUM), 0) AS AVG_PREMIUM
        FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED
        GROUP BY CUSTOMER_SEGMENT ORDER BY CUSTOMERS DESC
    """, "segment overview")
    if seg is not None:
        st.subheader("Customer Segments Overview")
        st.dataframe(seg, use_container_width=True, hide_index=True)
