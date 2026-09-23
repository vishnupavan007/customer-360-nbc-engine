import streamlit as st
from snowflake.snowpark.context import get_active_session
from utils import apply_theme, theme_sidebar, render_df

st.set_page_config(page_title="Customer 360 View", page_icon="👤", layout="wide")
apply_theme()

try:
    session = get_active_session()
except Exception as e:
    st.error(f"Could not connect to Snowflake: {e}")
    st.stop()

with st.sidebar:
    theme_sidebar()
    st.divider()

# ── Shared CSS (injected on each page load) ─────────────────────────────────
st.markdown("""
<style>
.badge { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:700; }
.badge-vip      { background:#F3E5F5; color:#6A1B9A; }
.badge-premium  { background:#E3F2FD; color:#0D47A1; }
.badge-standard { background:#E0F7FA; color:#006064; }
.badge-basic    { background:#EFEBE9; color:#4E342E; }
.badge-critical { background:#FFCDD2; color:#B71C1C; }
.badge-high     { background:#FFE0B2; color:#E65100; }
.badge-medium   { background:#FFF9C4; color:#F57F17; }
.badge-low      { background:#C8E6C9; color:#1B5E20; }
.badge-positive { background:#C8E6C9; color:#1B5E20; }
.badge-negative { background:#FFCDD2; color:#B71C1C; }
.badge-neutral  { background:#F5F5F5; color:#424242; }
.ai-card {
    background: linear-gradient(135deg, #E3F2FD 0%, #F3E5F5 100%);
    border-radius: 10px; padding: 16px; margin-top: 12px;
    border-left: 4px solid #29B5E8;
}
</style>
""", unsafe_allow_html=True)


def seg_badge(seg):
    return f'<span class="badge badge-{seg.lower()}">{seg}</span>'


def risk_badge(urgency):
    return f'<span class="badge badge-{urgency.lower()}">{urgency}</span>'


st.title("Customer 360 View")
st.caption("Search and explore unified customer profiles")

search_term = st.text_input("Search by customer name or ID", placeholder="e.g. Robert Tanaka or 831530")

VALID_SEGMENTS = {"Basic", "Standard", "Premium", "VIP"}


def safe_sql(query, error_label="data"):
    try:
        return session.sql(query).to_pandas()
    except Exception as e:
        st.error(f"Could not load {error_label}: {e}")
        return None


if search_term:
    search_stripped = search_term.strip()
    if search_stripped.isdigit():
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
            seg = row["CUSTOMER_SEGMENT"]
            label = f"{row['FULL_NAME']} (ID: {cid})  •  {seg}"
            with st.expander(label, expanded=len(customers) == 1):
                # ── Top KPI row ──────────────────────────────────────────
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Credit Score", row["CREDIT_SCORE"])
                c2.metric("Annual Income", f"${row['ANNUAL_INCOME']:,.0f}")
                c3.metric("Est. CLV", f"${row['ESTIMATED_CLV']:,.0f}")
                c4.metric("Risk Level", row["COMPOSITE_RISK_LEVEL"])

                # Segment + status badges
                active_label = "Active" if row["IS_ACTIVE"] else "Inactive"
                active_color = "low" if row["IS_ACTIVE"] else "negative"
                st.markdown(
                    f'{seg_badge(seg)} &nbsp; <span class="badge badge-{active_color}">{active_label}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown("")

                active_tab = st.radio(
                    "Section", ["Profile", "Policies & Claims", "Loans", "Interactions"],
                    key=f"tab_{cid}"
                )

                if active_tab == "Profile":
                    p1, p2 = st.columns(2)
                    with p1:
                        st.markdown(
                            f"- **Email**: {row['EMAIL']}\n"
                            f"- **Phone**: {row['PHONE']}\n"
                            f"- **Location**: {row['CITY']}, {row['STATE']}, {row['COUNTRY']}"
                        )
                    with p2:
                        st.markdown(
                            f"- **Age**: {row['AGE']}\n"
                            f"- **Tenure**: {row['TENURE_MONTHS']} months\n"
                            f"- **Complaints**: {int(row['COMPLAINT_COUNT'])}"
                        )

                elif active_tab == "Policies & Claims":
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
                        render_df(claims)

                elif active_tab == "Loans":
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
                        render_df(loans)

                elif active_tab == "Interactions":
                    timeline = safe_sql(
                        f"SELECT EVENT_DATE, EVENT_CATEGORY, EVENT_DESCRIPTION, EVENT_STATUS"
                        f" FROM CUSTOMER_360.CURATED.CUSTOMER_INTERACTION_TIMELINE"
                        f" WHERE CUSTOMER_ID = {cid} ORDER BY EVENT_DATE DESC LIMIT 20",
                        "timeline"
                    )
                    if timeline is not None and not timeline.empty:
                        render_df(timeline)

                # ── AI Insights ──────────────────────────────────────────
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
                    score = float(churn_nba["CHURN_RISK_SCORE"].iloc[0] or 0)
                    urgency = churn_nba["RETENTION_URGENCY"].iloc[0] or "N/A"
                    conf = float(churn_nba["MODEL_CONFIDENCE"].iloc[0] or 0)
                    action = churn_nba["ACTION_TYPE"].iloc[0]

                    # Color the churn score
                    if score >= 0.8:
                        score_color = "#B71C1C"
                    elif score >= 0.6:
                        score_color = "#E65100"
                    elif score >= 0.4:
                        score_color = "#F57F17"
                    else:
                        score_color = "#2E7D32"

                    st.markdown(
                        f'<div class="ai-card">'
                        f'<strong>AI Insights</strong>&nbsp;&nbsp;'
                        f'Churn Risk: <span style="font-size:1.3rem;font-weight:800;color:{score_color}">{score:.2f}</span>'
                        f'&nbsp;&nbsp;{risk_badge(urgency)}'
                        f'&nbsp;&nbsp;Confidence: <strong>{conf:.0%}</strong>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if action:
                        priority = churn_nba["PRIORITY"].iloc[0] or ""
                        channel = churn_nba["RECOMMENDED_CHANNEL"].iloc[0] or ""
                        desc = churn_nba["ACTION_DESCRIPTION"].iloc[0] or ""
                        rationale = churn_nba["RATIONALE"].iloc[0] or ""
                        st.info(
                            f"**{action}** ({priority} priority via {channel})\n\n"
                            f"{desc}\n\n*{rationale}*"
                        )
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
        render_df(seg)
