import streamlit as st

st.set_page_config(page_title="Customer 360 View", page_icon="👤", layout="wide")
conn = st.connection("snowflake")

st.title("Customer 360 View")
st.caption("Search and explore unified customer profiles")

search_term = st.text_input("Search by customer name or ID", placeholder="e.g. James Smith or 42")

if search_term:
    if search_term.isdigit():
        where_clause = f"WHERE c.CUSTOMER_ID = {int(search_term)}"
    else:
        where_clause = f"WHERE LOWER(c.FULL_NAME) LIKE '%{search_term.lower()}%'"

    customers = conn.query(f"""
        SELECT
            c.CUSTOMER_ID, c.FULL_NAME, c.EMAIL, c.PHONE, c.CUSTOMER_SEGMENT,
            c.CITY, c.STATE, c.COUNTRY, c.AGE, c.CREDIT_SCORE, c.ANNUAL_INCOME,
            c.IS_ACTIVE, c.TENURE_MONTHS, c.TOTAL_POLICIES, c.ACTIVE_POLICIES,
            c.TOTAL_PREMIUM, c.TOTAL_CLAIMS, c.OPEN_CLAIMS, c.TOTAL_LOANS,
            c.TOTAL_OUTSTANDING_BALANCE, c.MAX_DAYS_PAST_DUE,
            c.COMPLAINT_COUNT, c.TOTAL_CALLS, c.COMPOSITE_RISK_LEVEL,
            ROUND(c.ESTIMATED_CLV, 0) AS ESTIMATED_CLV
        FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
        {where_clause}
        LIMIT 20
    """)

    if customers.empty:
        st.warning("No customers found.")
    else:
        for _, row in customers.iterrows():
            with st.expander(f"{row['FULL_NAME']} (ID: {row['CUSTOMER_ID']}) - {row['CUSTOMER_SEGMENT']}", expanded=len(customers) == 1):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Credit Score", row['CREDIT_SCORE'])
                c2.metric("Annual Income", f"${row['ANNUAL_INCOME']:,.0f}")
                c3.metric("Est. CLV", f"${row['ESTIMATED_CLV']:,.0f}")
                c4.metric("Risk Level", row['COMPOSITE_RISK_LEVEL'])

                tab1, tab2, tab3, tab4 = st.tabs(["Profile", "Policies & Claims", "Loans", "Interactions"])

                with tab1:
                    p1, p2 = st.columns(2)
                    with p1:
                        st.markdown(f"""
                        - **Email**: {row['EMAIL']}
                        - **Phone**: {row['PHONE']}
                        - **Location**: {row['CITY']}, {row['STATE']}, {row['COUNTRY']}
                        """)
                    with p2:
                        st.markdown(f"""
                        - **Age**: {row['AGE']}
                        - **Tenure**: {row['TENURE_MONTHS']} months
                        - **Active**: {'Yes' if row['IS_ACTIVE'] else 'No'}
                        """)

                with tab2:
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Total Policies", int(row['TOTAL_POLICIES']))
                    m2.metric("Active Policies", int(row['ACTIVE_POLICIES']))
                    m3.metric("Total Premium", f"${row['TOTAL_PREMIUM']:,.0f}")
                    m4.metric("Open Claims", int(row['OPEN_CLAIMS']))

                    claims = conn.query(f"""
                        SELECT CLAIM_ID, CLAIM_TYPE, CLAIM_STATUS,
                               CLAIM_AMOUNT, SETTLEMENT_AMOUNT, FILED_DATE, DESCRIPTION
                        FROM CUSTOMER_360.CLEAN.DT_CLAIMS
                        WHERE CUSTOMER_ID = {row['CUSTOMER_ID']}
                        ORDER BY FILED_DATE DESC LIMIT 10
                    """)
                    if not claims.empty:
                        st.dataframe(claims, use_container_width=True, hide_index=True)

                with tab3:
                    l1, l2, l3 = st.columns(3)
                    l1.metric("Total Loans", int(row['TOTAL_LOANS']))
                    l2.metric("Outstanding Balance", f"${row['TOTAL_OUTSTANDING_BALANCE']:,.0f}")
                    l3.metric("Max Days Past Due", int(row['MAX_DAYS_PAST_DUE']))

                    loans = conn.query(f"""
                        SELECT LOAN_ID, LOAN_TYPE, LOAN_STATUS, PRINCIPAL_AMOUNT,
                               INTEREST_RATE, MONTHLY_PAYMENT, OUTSTANDING_BALANCE,
                               DAYS_PAST_DUE, DELINQUENCY_CATEGORY
                        FROM CUSTOMER_360.CLEAN.DT_LOANS
                        WHERE CUSTOMER_ID = {row['CUSTOMER_ID']}
                        ORDER BY ORIGINATION_DATE DESC LIMIT 10
                    """)
                    if not loans.empty:
                        st.dataframe(loans, use_container_width=True, hide_index=True)

                with tab4:
                    i1, i2 = st.columns(2)
                    i1.metric("Total Interactions", int(row['COMPLAINT_COUNT'] + row['TOTAL_CALLS']))
                    i2.metric("Complaints", int(row['COMPLAINT_COUNT']))

                    timeline = conn.query(f"""
                        SELECT EVENT_DATE, EVENT_CATEGORY, EVENT_DESCRIPTION,
                               EVENT_STATUS, EVENT_AMOUNT
                        FROM CUSTOMER_360.CURATED.CUSTOMER_INTERACTION_TIMELINE
                        WHERE CUSTOMER_ID = {row['CUSTOMER_ID']}
                        ORDER BY EVENT_DATE DESC LIMIT 20
                    """)
                    if not timeline.empty:
                        st.dataframe(timeline, use_container_width=True, hide_index=True)

                # Churn risk and NBA
                churn_nba = conn.query(f"""
                    SELECT
                        cr.CHURN_RISK_SCORE, cr.RETENTION_URGENCY, cr.MODEL_CONFIDENCE,
                        nba.ACTION_TYPE, nba.ACTION_DESCRIPTION, nba.PRIORITY,
                        nba.RECOMMENDED_CHANNEL, nba.RATIONALE
                    FROM CUSTOMER_360.AI.DT_CHURN_RISK cr
                    LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba
                        ON cr.CUSTOMER_ID = nba.CUSTOMER_ID
                    WHERE cr.CUSTOMER_ID = {row['CUSTOMER_ID']}
                """)
                if not churn_nba.empty:
                    st.subheader("AI Insights")
                    ai1, ai2, ai3 = st.columns(3)
                    ai1.metric("Churn Risk", f"{churn_nba['CHURN_RISK_SCORE'].iloc[0]:.2f}")
                    ai2.metric("Urgency", churn_nba['RETENTION_URGENCY'].iloc[0] or "N/A")
                    ai3.metric("Confidence", f"{(churn_nba['MODEL_CONFIDENCE'].iloc[0] or 0):.0%}")

                    if churn_nba['ACTION_TYPE'].iloc[0]:
                        st.info(f"**Recommended Action ({churn_nba['PRIORITY'].iloc[0]})**: "
                                f"{churn_nba['ACTION_DESCRIPTION'].iloc[0]}\n\n"
                                f"**Channel**: {churn_nba['RECOMMENDED_CHANNEL'].iloc[0]} | "
                                f"**Rationale**: {churn_nba['RATIONALE'].iloc[0]}")
else:
    st.info("Enter a customer name or ID to search.")

    segment_summary = conn.query("""
        SELECT CUSTOMER_SEGMENT, COUNT(*) AS CUSTOMERS,
               SUM(CASE WHEN IS_ACTIVE THEN 1 ELSE 0 END) AS ACTIVE,
               ROUND(AVG(CREDIT_SCORE), 0) AS AVG_CREDIT_SCORE,
               ROUND(AVG(TOTAL_PREMIUM), 0) AS AVG_PREMIUM
        FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED
        GROUP BY CUSTOMER_SEGMENT
        ORDER BY CUSTOMERS DESC
    """)
    st.subheader("Customer Segments Overview")
    st.dataframe(segment_summary, use_container_width=True, hide_index=True)
