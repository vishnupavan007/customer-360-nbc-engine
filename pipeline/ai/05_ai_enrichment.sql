-- =============================================================================
-- 05_ai_enrichment.sql - AI Schema
-- Sentiment analysis, churn risk scoring, next best action, Cortex Search
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE WAREHOUSE COMPUTE_WH;

-- =========================================================================
-- DT_TRANSCRIPT_SENTIMENT - Sentiment + summarization on call transcripts
-- Uses SNOWFLAKE.CORTEX.SENTIMENT and SNOWFLAKE.CORTEX.SUMMARIZE
-- =========================================================================
CREATE OR REPLACE DYNAMIC TABLE AI.DT_TRANSCRIPT_SENTIMENT
  TARGET_LAG = '5 minutes'
  WAREHOUSE = COMPUTE_WH
AS
WITH scored AS (
    SELECT
        t.TRANSCRIPT_ID,
        t.CUSTOMER_ID,
        t.CALL_DATE,
        t.CALL_REASON,
        t.AGENT_NAME,
        t.DURATION_SECONDS,
        t.TRANSCRIPT_TEXT,
        -- Call SENTIMENT once per row to avoid double billing
        SNOWFLAKE.CORTEX.SENTIMENT(t.TRANSCRIPT_TEXT) AS SENTIMENT_SCORE,
        SNOWFLAKE.CORTEX.SUMMARIZE(t.TRANSCRIPT_TEXT) AS CALL_SUMMARY
    FROM CLEAN.DT_CALL_TRANSCRIPTS t
)
SELECT
    TRANSCRIPT_ID,
    CUSTOMER_ID,
    CALL_DATE,
    CALL_REASON,
    AGENT_NAME,
    DURATION_SECONDS,
    TRANSCRIPT_TEXT,
    SENTIMENT_SCORE,
    CASE
        WHEN SENTIMENT_SCORE >= 0.3 THEN 'Positive'
        WHEN SENTIMENT_SCORE <= -0.3 THEN 'Negative'
        ELSE 'Neutral'
    END AS SENTIMENT_LABEL,
    CALL_SUMMARY
FROM scored;


-- =========================================================================
-- DT_CHURN_RISK - AI-powered churn risk scoring
-- Uses SNOWFLAKE.CORTEX.COMPLETE for structured JSON risk assessment
-- =========================================================================
CREATE OR REPLACE DYNAMIC TABLE AI.DT_CHURN_RISK
  TARGET_LAG = '1 hour'
  WAREHOUSE = COMPUTE_WH
AS
WITH latest_sentiment AS (
    SELECT
        CUSTOMER_ID,
        AVG(SENTIMENT_SCORE) AS AVG_SENTIMENT_SCORE,
        MIN(SENTIMENT_SCORE) AS WORST_SENTIMENT_SCORE,
        COUNT(CASE WHEN SENTIMENT_LABEL = 'Negative' THEN 1 END) AS NEGATIVE_CALL_COUNT
    FROM AI.DT_TRANSCRIPT_SENTIMENT
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
        'You are a customer risk analyst for an insurance and lending company. ' ||
        'Analyze this customer profile and return ONLY a valid JSON object with these exact keys: ' ||
        'churn_risk_score (float 0.0 to 1.0 where 1.0 is highest risk), ' ||
        'risk_factors (array of up to 4 short strings describing key risk drivers), ' ||
        'retention_urgency (string: Critical, High, Medium, or Low), ' ||
        'confidence (float 0.0 to 1.0). ' ||
        'Customer data: ' ||
        'segment=' || c.CUSTOMER_SEGMENT ||
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
    -- NOTE: llama3.1-8b wraps JSON in markdown code fences (```json...```).
    -- REGEXP_SUBSTR extracts the JSON object so TRY_PARSE_JSON can parse it.
    TRY_PARSE_JSON(REGEXP_SUBSTR(CHURN_RISK_RAW, '\\{[\\s\\S]*\\}')):churn_risk_score::FLOAT AS CHURN_RISK_SCORE,
    TRY_PARSE_JSON(REGEXP_SUBSTR(CHURN_RISK_RAW, '\\{[\\s\\S]*\\}')):retention_urgency::VARCHAR AS RETENTION_URGENCY,
    TRY_PARSE_JSON(REGEXP_SUBSTR(CHURN_RISK_RAW, '\\{[\\s\\S]*\\}')):risk_factors::ARRAY AS RISK_FACTORS,
    TRY_PARSE_JSON(REGEXP_SUBSTR(CHURN_RISK_RAW, '\\{[\\s\\S]*\\}')):confidence::FLOAT AS MODEL_CONFIDENCE
FROM CURATED.CUSTOMER_360_UNIFIED c
LEFT JOIN latest_sentiment s ON c.CUSTOMER_ID = s.CUSTOMER_ID;


-- =========================================================================
-- DT_NEXT_BEST_ACTION - AI-recommended actions per customer
-- Combines churn risk + sentiment + profile for personalized recommendations
-- =========================================================================
CREATE OR REPLACE DYNAMIC TABLE AI.DT_NEXT_BEST_ACTION
  TARGET_LAG = '1 hour'
  WAREHOUSE = COMPUTE_WH
AS
WITH latest_call AS (
    SELECT
        CUSTOMER_ID,
        CALL_SUMMARY,
        SENTIMENT_SCORE AS LATEST_SENTIMENT_SCORE,
        SENTIMENT_LABEL AS LATEST_SENTIMENT_LABEL,
        CALL_REASON AS LATEST_CALL_REASON
    FROM AI.DT_TRANSCRIPT_SENTIMENT
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
        'You are an insurance and lending customer success advisor. ' ||
        'Based on this customer profile, recommend the SINGLE best next action to take. ' ||
        'Return ONLY a valid JSON object with these exact keys: ' ||
        'action_type (one of: Retention_Offer, Policy_Review, Claims_Followup, Upsell, Payment_Assistance, Proactive_Outreach, Renewal_Reminder, Complaint_Resolution), ' ||
        'action_description (1-2 sentence specific recommendation), ' ||
        'priority (High, Medium, or Low), ' ||
        'channel (Email, Phone, InApp, or Branch), ' ||
        'rationale (1 sentence why this action). ' ||
        'Customer: ' ||
        'name=' || cr.FULL_NAME ||
        ', segment=' || cr.CUSTOMER_SEGMENT ||
        ', churn_risk=' || COALESCE(cr.CHURN_RISK_SCORE::VARCHAR, 'unknown') ||
        ', retention_urgency=' || COALESCE(cr.RETENTION_URGENCY, 'unknown') ||
        ', active_policies=' || u.ACTIVE_POLICIES::VARCHAR ||
        ', total_premium=$' || u.TOTAL_PREMIUM::VARCHAR ||
        ', open_claims=' || u.OPEN_CLAIMS::VARCHAR ||
        ', days_to_renewal=' || COALESCE(u.NEXT_RENEWAL_DAYS::VARCHAR, 'none') ||
        ', days_past_due=' || u.MAX_DAYS_PAST_DUE::VARCHAR ||
        ', estimated_clv=$' || ROUND(u.ESTIMATED_CLV, 0)::VARCHAR ||
        ', latest_call_sentiment=' || COALESCE(lc.LATEST_SENTIMENT_LABEL, 'no_calls') ||
        ', latest_call_reason=' || COALESCE(lc.LATEST_CALL_REASON, 'none') ||
        ', latest_call_summary=' || COALESCE(LEFT(lc.CALL_SUMMARY, 300), 'no recent calls')
    ) AS NBA_RAW,
    -- NOTE: llama3.1-8b wraps JSON in markdown code fences (```json...```).
    -- REGEXP_SUBSTR extracts the JSON object so TRY_PARSE_JSON can parse it.
    TRY_PARSE_JSON(REGEXP_SUBSTR(NBA_RAW, '\\{[\\s\\S]*\\}')):action_type::VARCHAR AS ACTION_TYPE,
    TRY_PARSE_JSON(REGEXP_SUBSTR(NBA_RAW, '\\{[\\s\\S]*\\}')):action_description::VARCHAR AS ACTION_DESCRIPTION,
    TRY_PARSE_JSON(REGEXP_SUBSTR(NBA_RAW, '\\{[\\s\\S]*\\}')):priority::VARCHAR AS PRIORITY,
    TRY_PARSE_JSON(REGEXP_SUBSTR(NBA_RAW, '\\{[\\s\\S]*\\}')):channel::VARCHAR AS RECOMMENDED_CHANNEL,
    TRY_PARSE_JSON(REGEXP_SUBSTR(NBA_RAW, '\\{[\\s\\S]*\\}')):rationale::VARCHAR AS RATIONALE
FROM AI.DT_CHURN_RISK cr
LEFT JOIN latest_call lc ON cr.CUSTOMER_ID = lc.CUSTOMER_ID
LEFT JOIN CURATED.CUSTOMER_360_UNIFIED u ON cr.CUSTOMER_ID = u.CUSTOMER_ID
WHERE cr.CHURN_RISK_SCORE IS NOT NULL;


-- =========================================================================
-- CORTEX SEARCH SERVICE - Unstructured search over interactions + transcripts
-- Enables RAG for the Cortex Agent
-- =========================================================================
CREATE OR REPLACE CORTEX SEARCH SERVICE AI.INTERACTION_SEARCH_SERVICE
  ON SEARCH_TEXT
  ATTRIBUTES CUSTOMER_ID, SOURCE_TYPE, CHANNEL, EVENT_DATE
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 hour'
AS
SELECT
    CUSTOMER_ID::VARCHAR AS CUSTOMER_ID,
    TRANSCRIPT_TEXT AS SEARCH_TEXT,
    'call_transcript' AS SOURCE_TYPE,
    'Phone' AS CHANNEL,
    CALL_DATE AS EVENT_DATE
FROM CLEAN.DT_CALL_TRANSCRIPTS

UNION ALL

SELECT
    CUSTOMER_ID::VARCHAR AS CUSTOMER_ID,
    COALESCE(SUBJECT, '') || '. ' || COALESCE(NOTES, '') AS SEARCH_TEXT,
    'interaction_note' AS SOURCE_TYPE,
    CHANNEL,
    INTERACTION_DATE AS EVENT_DATE
FROM CLEAN.DT_INTERACTIONS
WHERE NOTES IS NOT NULL AND LENGTH(TRIM(NOTES)) > 0;
