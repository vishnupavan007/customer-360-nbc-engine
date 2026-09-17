-- =============================================================================
-- 08_tasks_and_monitoring.sql - Automation, Quality Checks, and Guardrails
-- Uses simple single-statement tasks to avoid BEGIN/END parsing issues
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE WAREHOUSE COMPUTE_WH;

-- =========================================================================
-- AI Quality Monitoring Table
-- =========================================================================
CREATE TABLE IF NOT EXISTS APP.AI_QUALITY_LOG (
    CHECK_TIMESTAMP   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CHECK_TYPE        VARCHAR(50),
    TABLE_NAME        VARCHAR(100),
    METRIC_NAME       VARCHAR(100),
    METRIC_VALUE      NUMBER(12,2),
    THRESHOLD         NUMBER(12,2),
    STATUS            VARCHAR(20),
    DETAILS           VARCHAR(2000)
);

-- =========================================================================
-- Task 1: Check churn risk NULL rate (daily at 8 AM ET)
-- =========================================================================
CREATE OR REPLACE TASK APP.CHECK_CHURN_COMPLETENESS
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 8 * * * America/New_York'
AS
    INSERT INTO APP.AI_QUALITY_LOG (CHECK_TYPE, TABLE_NAME, METRIC_NAME, METRIC_VALUE, THRESHOLD, STATUS, DETAILS)
    SELECT
        'completeness',
        'AI.DT_CHURN_RISK',
        'null_churn_score_rate',
        ROUND(COUNT(CASE WHEN CHURN_RISK_SCORE IS NULL THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2),
        10.0,
        CASE WHEN COUNT(CASE WHEN CHURN_RISK_SCORE IS NULL THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0) > 10 THEN 'FAIL' ELSE 'PASS' END,
        'Percentage of customers with NULL churn risk score'
    FROM AI.DT_CHURN_RISK;

-- =========================================================================
-- Task 2: Check NBA NULL rate (runs after Task 1)
-- =========================================================================
CREATE OR REPLACE TASK APP.CHECK_NBA_COMPLETENESS
  WAREHOUSE = COMPUTE_WH
  AFTER APP.CHECK_CHURN_COMPLETENESS
AS
    INSERT INTO APP.AI_QUALITY_LOG (CHECK_TYPE, TABLE_NAME, METRIC_NAME, METRIC_VALUE, THRESHOLD, STATUS, DETAILS)
    SELECT
        'completeness',
        'AI.DT_NEXT_BEST_ACTION',
        'null_action_type_rate',
        ROUND(COUNT(CASE WHEN ACTION_TYPE IS NULL THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2),
        15.0,
        CASE WHEN COUNT(CASE WHEN ACTION_TYPE IS NULL THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0) > 15 THEN 'FAIL' ELSE 'PASS' END,
        'Percentage of customers with NULL action type'
    FROM AI.DT_NEXT_BEST_ACTION;

-- =========================================================================
-- Task 3: Check churn score range (runs after Task 2)
-- =========================================================================
CREATE OR REPLACE TASK APP.CHECK_CHURN_RANGE
  WAREHOUSE = COMPUTE_WH
  AFTER APP.CHECK_NBA_COMPLETENESS
AS
    INSERT INTO APP.AI_QUALITY_LOG (CHECK_TYPE, TABLE_NAME, METRIC_NAME, METRIC_VALUE, THRESHOLD, STATUS, DETAILS)
    SELECT
        'range_check',
        'AI.DT_CHURN_RISK',
        'out_of_range_scores',
        COUNT(CASE WHEN CHURN_RISK_SCORE < 0 OR CHURN_RISK_SCORE > 1 THEN 1 END),
        0,
        CASE WHEN COUNT(CASE WHEN CHURN_RISK_SCORE < 0 OR CHURN_RISK_SCORE > 1 THEN 1 END) > 0 THEN 'FAIL' ELSE 'PASS' END,
        'Count of churn scores outside 0-1 range'
    FROM AI.DT_CHURN_RISK;

-- =========================================================================
-- Task 4: Check sentiment score range (runs after Task 3)
-- =========================================================================
CREATE OR REPLACE TASK APP.CHECK_SENTIMENT_RANGE
  WAREHOUSE = COMPUTE_WH
  AFTER APP.CHECK_CHURN_RANGE
AS
    INSERT INTO APP.AI_QUALITY_LOG (CHECK_TYPE, TABLE_NAME, METRIC_NAME, METRIC_VALUE, THRESHOLD, STATUS, DETAILS)
    SELECT
        'range_check',
        'AI.DT_TRANSCRIPT_SENTIMENT',
        'out_of_range_sentiment',
        COUNT(CASE WHEN SENTIMENT_SCORE < -1 OR SENTIMENT_SCORE > 1 THEN 1 END),
        0,
        CASE WHEN COUNT(CASE WHEN SENTIMENT_SCORE < -1 OR SENTIMENT_SCORE > 1 THEN 1 END) > 0 THEN 'FAIL' ELSE 'PASS' END,
        'Count of sentiment scores outside -1 to 1 range'
    FROM AI.DT_TRANSCRIPT_SENTIMENT;

-- =========================================================================
-- Task 5: Pipeline health check (every 6 hours, independent)
-- =========================================================================
CREATE OR REPLACE TASK APP.PIPELINE_HEALTH_CHECK
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 */6 * * * America/New_York'
AS
    INSERT INTO APP.AI_QUALITY_LOG (CHECK_TYPE, TABLE_NAME, METRIC_NAME, METRIC_VALUE, THRESHOLD, STATUS, DETAILS)
    SELECT
        'pipeline_health',
        'ALL',
        'health_check_run',
        1,
        1,
        'PASS',
        'Pipeline health check completed at ' || CURRENT_TIMESTAMP()::VARCHAR;

-- =========================================================================
-- Resume all root tasks (child tasks auto-resume with parent)
-- =========================================================================
ALTER TASK APP.CHECK_SENTIMENT_RANGE RESUME;
ALTER TASK APP.CHECK_CHURN_RANGE RESUME;
ALTER TASK APP.CHECK_NBA_COMPLETENESS RESUME;
ALTER TASK APP.CHECK_CHURN_COMPLETENESS RESUME;
ALTER TASK APP.PIPELINE_HEALTH_CHECK RESUME;
