-- =============================================================================
-- 14_ai_monitoring.sql
-- AI Output Monitoring for Customer 360
--
-- Creates Data Metric Functions (DMFs) to continuously monitor AI-generated
-- columns for parse failures, attaches them to dynamic tables on a
-- trigger-on-changes schedule, and builds a unified quality dashboard view.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Step 1: Data Metric Functions
-- ---------------------------------------------------------------------------

-- Measures the percentage of NULL churn risk scores (AI parse failures)
CREATE OR REPLACE DATA METRIC FUNCTION CUSTOMER_360.APP.CHURN_PARSE_FAILURE_RATE(
    ARG_T TABLE(CHURN_RISK_SCORE FLOAT)
)
RETURNS NUMBER
AS
$$
SELECT ROUND(100.0 * COUNT_IF(CHURN_RISK_SCORE IS NULL) / NULLIF(COUNT(*), 0), 2)
FROM ARG_T
$$;

-- Measures the percentage of NULL action types (AI parse failures)
CREATE OR REPLACE DATA METRIC FUNCTION CUSTOMER_360.APP.NBA_PARSE_FAILURE_RATE(
    ARG_T TABLE(ACTION_TYPE VARCHAR)
)
RETURNS NUMBER
AS
$$
SELECT ROUND(100.0 * COUNT_IF(ACTION_TYPE IS NULL) / NULLIF(COUNT(*), 0), 2)
FROM ARG_T
$$;

-- ---------------------------------------------------------------------------
-- Step 2: Attach DMFs to AI dynamic tables
-- ---------------------------------------------------------------------------

-- Churn Risk table
ALTER TABLE CUSTOMER_360.AI.DT_CHURN_RISK
SET DATA_METRIC_SCHEDULE = 'TRIGGER_ON_CHANGES';

ALTER TABLE CUSTOMER_360.AI.DT_CHURN_RISK
ADD DATA METRIC FUNCTION CUSTOMER_360.APP.CHURN_PARSE_FAILURE_RATE ON (CHURN_RISK_SCORE);

-- Next Best Action table
ALTER TABLE CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
SET DATA_METRIC_SCHEDULE = 'TRIGGER_ON_CHANGES';

ALTER TABLE CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
ADD DATA METRIC FUNCTION CUSTOMER_360.APP.NBA_PARSE_FAILURE_RATE ON (ACTION_TYPE);

-- ---------------------------------------------------------------------------
-- Step 3: Unified AI quality monitoring view
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW CUSTOMER_360.APP.AI_QUALITY_DASHBOARD AS
SELECT
    'Churn Risk' AS MODEL,
    COUNT(*) AS TOTAL_RECORDS,
    COUNT_IF(CHURN_RISK_SCORE IS NULL) AS PARSE_FAILURES,
    ROUND(100.0 * COUNT_IF(CHURN_RISK_SCORE IS NULL) / NULLIF(COUNT(*), 0), 2) AS FAILURE_RATE_PCT,
    COUNT_IF(CHURN_RISK_SCORE < 0 OR CHURN_RISK_SCORE > 1) AS OUT_OF_RANGE,
    AVG(CHURN_RISK_SCORE) AS AVG_SCORE
FROM CUSTOMER_360.AI.DT_CHURN_RISK
UNION ALL
SELECT
    'Next Best Action' AS MODEL,
    COUNT(*) AS TOTAL_RECORDS,
    COUNT_IF(ACTION_TYPE IS NULL) AS PARSE_FAILURES,
    ROUND(100.0 * COUNT_IF(ACTION_TYPE IS NULL) / NULLIF(COUNT(*), 0), 2) AS FAILURE_RATE_PCT,
    0 AS OUT_OF_RANGE,
    NULL AS AVG_SCORE
FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
UNION ALL
SELECT
    'Document Extraction' AS MODEL,
    COUNT(*) AS TOTAL_RECORDS,
    COUNT_IF(REFERENCE_NUMBER IS NULL AND CUSTOMER_NAME IS NULL) AS PARSE_FAILURES,
    ROUND(100.0 * COUNT_IF(REFERENCE_NUMBER IS NULL AND CUSTOMER_NAME IS NULL) / NULLIF(COUNT(*), 0), 2) AS FAILURE_RATE_PCT,
    0 AS OUT_OF_RANGE,
    NULL AS AVG_SCORE
FROM CUSTOMER_360.AI.DT_DOCUMENT_EXTRACTED;
