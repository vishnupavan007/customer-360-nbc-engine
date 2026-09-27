-- =============================================================================
-- 16_proactive_alerts.sql - Proactive Monitoring Alerts
-- Auto-fires email notifications on business-critical conditions
-- Transforms the platform from passive dashboard to active automation
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE SCHEMA APP;
USE WAREHOUSE COMPUTE_WH;

-- =========================================================================
-- Alert 1: Critical churn risk detection
-- Fires every 60 minutes when any customer has churn risk >= 0.8
-- with Critical retention urgency. Emails the customer list.
-- =========================================================================
CREATE OR REPLACE ALERT ALERT_HIGH_CHURN_RISK
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '60 MINUTES'
  IF (EXISTS (
    SELECT 1 FROM CUSTOMER_360.AI.DT_CHURN_RISK
    WHERE CHURN_RISK_SCORE >= 0.8
      AND RETENTION_URGENCY = 'Critical'
  ))
  THEN
    CALL SYSTEM$SEND_EMAIL(
      'customer_360_notifications',
      'suresh.erragana@gmail.com',
      'ALERT: Critical Churn Risk Detected - Customer 360',
      (SELECT 'Critical churn risk customers detected:\n\n' ||
        LISTAGG(FULL_NAME || ' (' || CUSTOMER_SEGMENT || ') - Score: ' || ROUND(CHURN_RISK_SCORE, 2)::VARCHAR || ' - ' || RETENTION_URGENCY, '\n')
        WITHIN GROUP (ORDER BY CHURN_RISK_SCORE DESC)
       FROM CUSTOMER_360.AI.DT_CHURN_RISK
       WHERE CHURN_RISK_SCORE >= 0.8 AND RETENTION_URGENCY = 'Critical')
    );

ALTER ALERT ALERT_HIGH_CHURN_RISK RESUME;


-- =========================================================================
-- Alert 2: AI model quality degradation
-- Fires every 6 hours when LLM parse failure rate exceeds 5%
-- for any model (churn, NBA, document extraction).
-- =========================================================================
CREATE OR REPLACE ALERT ALERT_AI_QUALITY_DEGRADATION
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '360 MINUTES'
  IF (EXISTS (
    SELECT 1 FROM CUSTOMER_360.APP.AI_QUALITY_DASHBOARD
    WHERE FAILURE_RATE_PCT > 5
  ))
  THEN
    CALL SYSTEM$SEND_EMAIL(
      'customer_360_notifications',
      'suresh.erragana@gmail.com',
      'ALERT: AI Model Quality Degradation - Customer 360',
      (SELECT LISTAGG(MODEL || ': ' || FAILURE_RATE_PCT::VARCHAR || '% failure rate (' || PARSE_FAILURES::VARCHAR || '/' || TOTAL_RECORDS::VARCHAR || ')', '\n')
        WITHIN GROUP (ORDER BY FAILURE_RATE_PCT DESC)
       FROM CUSTOMER_360.APP.AI_QUALITY_DASHBOARD
       WHERE FAILURE_RATE_PCT > 5)
    );

ALTER ALERT ALERT_AI_QUALITY_DEGRADATION RESUME;


-- =========================================================================
-- Alert 3: VIP/Premium customer at risk
-- Fires every 30 minutes when high-value customers have 3+ complaints
-- with High composite risk. Triggers immediate retention outreach.
-- =========================================================================
CREATE OR REPLACE ALERT ALERT_VIP_COMPLAINT
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '30 MINUTES'
  IF (EXISTS (
    SELECT 1 FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED
    WHERE CUSTOMER_SEGMENT IN ('VIP', 'Premium')
      AND COMPLAINT_COUNT >= 3
      AND COMPOSITE_RISK_LEVEL = 'High'
  ))
  THEN
    CALL SYSTEM$SEND_EMAIL(
      'customer_360_notifications',
      'suresh.erragana@gmail.com',
      'ALERT: High-Value Customer at Risk - Customer 360',
      (SELECT LISTAGG(FULL_NAME || ' (' || CUSTOMER_SEGMENT || ') - ' || COMPLAINT_COUNT::VARCHAR || ' complaints, Risk: ' || COMPOSITE_RISK_LEVEL, '\n')
        WITHIN GROUP (ORDER BY COMPLAINT_COUNT DESC)
       FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED
       WHERE CUSTOMER_SEGMENT IN ('VIP', 'Premium')
         AND COMPLAINT_COUNT >= 3
         AND COMPOSITE_RISK_LEVEL = 'High')
    );

ALTER ALERT ALERT_VIP_COMPLAINT RESUME;
