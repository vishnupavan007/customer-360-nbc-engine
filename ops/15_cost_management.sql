-- =============================================================================
-- 15_cost_management.sql - Cost Controls for Customer 360 Pipeline
-- Resource monitors, TARGET_LAG tuning, and credit guardrails
-- =============================================================================

USE DATABASE CUSTOMER_360;

-- =========================================================================
-- RESOURCE MONITOR - Monthly credit budget with alert and suspend triggers
-- 75% and 90% thresholds send notifications; 100% suspends the warehouse
-- to prevent runaway spend.
-- =========================================================================
CREATE OR REPLACE RESOURCE MONITOR CUSTOMER_360_MONITOR
  WITH CREDIT_QUOTA = 100
  FREQUENCY = MONTHLY
  START_TIMESTAMP = IMMEDIATELY
  TRIGGERS
    ON 75 PERCENT DO NOTIFY
    ON 90 PERCENT DO NOTIFY
    ON 100 PERCENT DO SUSPEND;

ALTER WAREHOUSE COMPUTE_WH SET RESOURCE_MONITOR = CUSTOMER_360_MONITOR;

-- =========================================================================
-- TARGET_LAG TUNING - Reduce AI dynamic table refresh frequency
--
-- The upstream raw data arrives via a daily batch pipeline (~every 6 hours).
-- Refreshing AI tables every 5 minutes triggers expensive LLM calls
-- (CORTEX.COMPLETE, CORTEX.SENTIMENT, CORTEX.SUMMARIZE) against unchanged
-- data. Setting TARGET_LAG to 60 minutes cuts unnecessary LLM invocations
-- by ~12x while still catching new data within an hour of arrival.
--
-- Document processing tables (DT_DOCUMENT_PARSED, DT_DOCUMENT_EXTRACTED)
-- keep 5-minute lag since document uploads can be ad-hoc.
-- =========================================================================
ALTER DYNAMIC TABLE CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT SET TARGET_LAG = '60 minutes';
ALTER DYNAMIC TABLE CUSTOMER_360.AI.DT_CHURN_RISK             SET TARGET_LAG = '60 minutes';
ALTER DYNAMIC TABLE CUSTOMER_360.AI.DT_NEXT_BEST_ACTION       SET TARGET_LAG = '60 minutes';
