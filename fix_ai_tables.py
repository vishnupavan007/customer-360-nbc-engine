"""Fix AI dynamic tables: extract JSON from LLM output that wraps JSON in markdown code blocks."""
import os
from dotenv import load_dotenv
import snowflake.connector

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    role="ACCOUNTADMIN",
    warehouse="COMPUTE_WH",
    database="CUSTOMER_360",
    schema="AI",
)

cur = conn.cursor()

# Fix 1: Recreate DT_CHURN_RISK with JSON extraction
print("Recreating DT_CHURN_RISK with JSON extraction fix...")
cur.execute("""
CREATE OR REPLACE DYNAMIC TABLE CUSTOMER_360.AI.DT_CHURN_RISK
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE = COMPUTE_WH
AS
WITH latest_sentiment AS (
    SELECT
        CUSTOMER_ID,
        AVG(SENTIMENT_SCORE) AS AVG_SENTIMENT_SCORE,
        MIN(SENTIMENT_SCORE) AS WORST_SENTIMENT_SCORE,
        COUNT(CASE WHEN SENTIMENT_LABEL = 'Negative' THEN 1 END) AS NEGATIVE_CALL_COUNT
    FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
    GROUP BY CUSTOMER_ID
)
SELECT
    c.CUSTOMER_ID,
    c.FULL_NAME,
    c.CUSTOMER_SEGMENT,
    c.TENURE_MONTHS,
    c.CREDIT_SCORE,
    c.IS_ACTIVE,
    c.ACTIVE_POLICIES,
    c.LAPSED_POLICIES,
    c.TOTAL_PREMIUM,
    c.OPEN_CLAIMS,
    c.DENIED_CLAIMS,
    c.COMPLAINT_COUNT,
    c.ESCALATION_COUNT,
    c.MAX_DAYS_PAST_DUE,
    c.PROBLEM_LOANS,
    c.DAYS_SINCE_LAST_INTERACTION,
    c.COMPOSITE_RISK_LEVEL,
    COALESCE(s.AVG_SENTIMENT_SCORE, 0) AS AVG_SENTIMENT_SCORE,
    COALESCE(s.NEGATIVE_CALL_COUNT, 0) AS NEGATIVE_CALL_COUNT,
    SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b',
        'You are a customer risk analyst. Return ONLY a raw JSON object, no markdown, no code blocks, no explanation. ' ||
        'Keys: churn_risk_score (float 0.0-1.0), risk_factors (array of strings), retention_urgency (Critical/High/Medium/Low), confidence (float 0.0-1.0). ' ||
        'Customer: segment=' || c.CUSTOMER_SEGMENT ||
        ', tenure_months=' || c.TENURE_MONTHS::VARCHAR ||
        ', credit_score=' || COALESCE(c.CREDIT_SCORE::VARCHAR, 'unknown') ||
        ', active_policies=' || c.ACTIVE_POLICIES::VARCHAR ||
        ', lapsed_policies=' || c.LAPSED_POLICIES::VARCHAR ||
        ', total_premium=' || c.TOTAL_PREMIUM::VARCHAR ||
        ', open_claims=' || c.OPEN_CLAIMS::VARCHAR ||
        ', denied_claims=' || c.DENIED_CLAIMS::VARCHAR ||
        ', complaint_count=' || c.COMPLAINT_COUNT::VARCHAR ||
        ', escalation_count=' || c.ESCALATION_COUNT::VARCHAR ||
        ', max_days_past_due=' || c.MAX_DAYS_PAST_DUE::VARCHAR ||
        ', problem_loans=' || c.PROBLEM_LOANS::VARCHAR ||
        ', days_since_last_interaction=' || c.DAYS_SINCE_LAST_INTERACTION::VARCHAR ||
        ', avg_call_sentiment=' || COALESCE(s.AVG_SENTIMENT_SCORE::VARCHAR, 'no_calls') ||
        ', negative_call_count=' || COALESCE(s.NEGATIVE_CALL_COUNT::VARCHAR, '0') ||
        ', is_active=' || c.IS_ACTIVE::VARCHAR
    ) AS CHURN_RISK_RAW,
    TRY_PARSE_JSON(
        REGEXP_SUBSTR(CHURN_RISK_RAW, '\\\\{[\\\\s\\\\S]*\\\\}')
    ) AS CHURN_RISK_JSON,
    CHURN_RISK_JSON:churn_risk_score::FLOAT AS CHURN_RISK_SCORE,
    CHURN_RISK_JSON:retention_urgency::VARCHAR AS RETENTION_URGENCY,
    CHURN_RISK_JSON:risk_factors::ARRAY AS RISK_FACTORS,
    CHURN_RISK_JSON:confidence::FLOAT AS MODEL_CONFIDENCE
FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
LEFT JOIN latest_sentiment s ON c.CUSTOMER_ID = s.CUSTOMER_ID
""")
print("DT_CHURN_RISK recreated:", cur.fetchone())

# Fix 2: Recreate DT_NEXT_BEST_ACTION with JSON extraction
print("\nRecreating DT_NEXT_BEST_ACTION with JSON extraction fix...")
cur.execute("""
CREATE OR REPLACE DYNAMIC TABLE CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE = COMPUTE_WH
AS
WITH latest_call AS (
    SELECT
        CUSTOMER_ID,
        CALL_SUMMARY,
        SENTIMENT_SCORE AS LATEST_SENTIMENT_SCORE,
        SENTIMENT_LABEL AS LATEST_SENTIMENT_LABEL,
        CALL_REASON AS LATEST_CALL_REASON
    FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
    QUALIFY ROW_NUMBER() OVER (PARTITION BY CUSTOMER_ID ORDER BY CALL_DATE DESC) = 1
)
SELECT
    cr.CUSTOMER_ID,
    cr.FULL_NAME,
    cr.CUSTOMER_SEGMENT,
    cr.CHURN_RISK_SCORE,
    cr.RETENTION_URGENCY,
    cr.RISK_FACTORS,
    COALESCE(lc.LATEST_SENTIMENT_SCORE, 0) AS LATEST_SENTIMENT_SCORE,
    lc.LATEST_SENTIMENT_LABEL,
    lc.LATEST_CALL_REASON,
    lc.CALL_SUMMARY AS LATEST_CALL_SUMMARY,
    u.TOTAL_PREMIUM,
    u.ACTIVE_POLICIES,
    u.OPEN_CLAIMS,
    u.NEXT_RENEWAL_DAYS,
    u.MAX_DAYS_PAST_DUE,
    u.ESTIMATED_CLV,
    SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b',
        'You are an insurance/lending advisor. Return ONLY a raw JSON object, no markdown, no code blocks, no explanation. ' ||
        'Keys: action_type (one of: Retention_Offer, Policy_Review, Claims_Followup, Upsell, Payment_Assistance, Proactive_Outreach, Renewal_Reminder, Complaint_Resolution), ' ||
        'action_description (1-2 sentences), priority (High/Medium/Low), channel (Email/Phone/InApp/Branch), rationale (1 sentence). ' ||
        'Customer: name=' || cr.FULL_NAME ||
        ', segment=' || cr.CUSTOMER_SEGMENT ||
        ', churn_risk=' || COALESCE(cr.CHURN_RISK_SCORE::VARCHAR, 'unknown') ||
        ', urgency=' || COALESCE(cr.RETENTION_URGENCY, 'unknown') ||
        ', active_policies=' || u.ACTIVE_POLICIES::VARCHAR ||
        ', premium=$' || u.TOTAL_PREMIUM::VARCHAR ||
        ', open_claims=' || u.OPEN_CLAIMS::VARCHAR ||
        ', days_to_renewal=' || COALESCE(u.NEXT_RENEWAL_DAYS::VARCHAR, 'none') ||
        ', days_past_due=' || u.MAX_DAYS_PAST_DUE::VARCHAR ||
        ', clv=$' || ROUND(u.ESTIMATED_CLV, 0)::VARCHAR ||
        ', last_sentiment=' || COALESCE(lc.LATEST_SENTIMENT_LABEL, 'no_calls') ||
        ', last_call_reason=' || COALESCE(lc.LATEST_CALL_REASON, 'none')
    ) AS NBA_RAW,
    TRY_PARSE_JSON(
        REGEXP_SUBSTR(NBA_RAW, '\\\\{[\\\\s\\\\S]*\\\\}')
    ) AS NBA_JSON,
    NBA_JSON:action_type::VARCHAR AS ACTION_TYPE,
    NBA_JSON:action_description::VARCHAR AS ACTION_DESCRIPTION,
    NBA_JSON:priority::VARCHAR AS PRIORITY,
    NBA_JSON:channel::VARCHAR AS RECOMMENDED_CHANNEL,
    NBA_JSON:rationale::VARCHAR AS RATIONALE
FROM CUSTOMER_360.AI.DT_CHURN_RISK cr
LEFT JOIN latest_call lc ON cr.CUSTOMER_ID = lc.CUSTOMER_ID
LEFT JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED u ON cr.CUSTOMER_ID = u.CUSTOMER_ID
""")
print("DT_NEXT_BEST_ACTION recreated:", cur.fetchone())

print("\nDynamic tables will refresh automatically. Check in a few minutes:")
print("  SELECT COUNT(*), COUNT(CHURN_RISK_SCORE) FROM CUSTOMER_360.AI.DT_CHURN_RISK;")
print("  SELECT COUNT(*), COUNT(ACTION_TYPE) FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION;")

conn.close()
print("\nDone.")
