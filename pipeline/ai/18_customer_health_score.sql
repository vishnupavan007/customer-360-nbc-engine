-- =============================================================================
-- 18_customer_health_score.sql - Composite Customer Health Score
-- Business-friendly A-F grade combining churn risk, sentiment, claims,
-- payment health, and loyalty into a single actionable metric
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE WAREHOUSE COMPUTE_WH;

CREATE OR REPLACE DYNAMIC TABLE AI.DT_CUSTOMER_HEALTH_SCORE
  TARGET_LAG = '60 minutes'
  WAREHOUSE = COMPUTE_WH
AS
WITH scored AS (
    SELECT
        c.CUSTOMER_ID,
        c.FULL_NAME,
        c.CUSTOMER_SEGMENT,
        c.IS_ACTIVE,
        -- Retention score (0-100): inverse of churn risk
        ROUND(100 - COALESCE(cr.CHURN_RISK_SCORE, 0.5) * 100, 1) AS RETENTION_SCORE,
        -- Sentiment score (0-100): normalized from [-1, 1]
        ROUND(CASE
            WHEN s.AVG_SENTIMENT IS NULL THEN 50
            ELSE GREATEST(0, LEAST(100, (s.AVG_SENTIMENT + 1) * 50))
        END, 1) AS SENTIMENT_SCORE,
        -- Claims health (0-100): penalized by open claims and overdue days
        ROUND(CASE
            WHEN c.TOTAL_CLAIMS = 0 THEN 80
            WHEN c.OPEN_CLAIMS = 0 AND c.TOTAL_CLAIMS > 0 THEN 90
            ELSE GREATEST(0, 100 - c.OPEN_CLAIMS * 20 - COALESCE(c.MAX_DAYS_PAST_DUE, 0) * 0.5)
        END, 1) AS CLAIMS_HEALTH,
        -- Payment health (0-100): based on days past due
        ROUND(CASE
            WHEN c.TOTAL_LOANS = 0 THEN 85
            WHEN c.MAX_DAYS_PAST_DUE = 0 THEN 95
            WHEN c.MAX_DAYS_PAST_DUE < 30 THEN 70
            WHEN c.MAX_DAYS_PAST_DUE < 90 THEN 40
            ELSE 10
        END, 1) AS PAYMENT_HEALTH,
        -- Loyalty score (0-100): based on tenure
        ROUND(CASE
            WHEN c.TENURE_MONTHS >= 60 THEN 95
            WHEN c.TENURE_MONTHS >= 36 THEN 80
            WHEN c.TENURE_MONTHS >= 12 THEN 60
            ELSE 40
        END, 1) AS LOYALTY_SCORE
    FROM CURATED.CUSTOMER_360_UNIFIED c
    LEFT JOIN AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID = cr.CUSTOMER_ID
    LEFT JOIN (
        SELECT CUSTOMER_ID, AVG(SENTIMENT_SCORE) AS AVG_SENTIMENT
        FROM AI.DT_TRANSCRIPT_SENTIMENT
        GROUP BY CUSTOMER_ID
    ) s ON c.CUSTOMER_ID = s.CUSTOMER_ID
)
SELECT
    *,
    -- Weighted composite: Retention(30%) + Payment(20%) + Sentiment(20%) + Claims(15%) + Loyalty(15%)
    ROUND(
        RETENTION_SCORE * 0.30 +
        SENTIMENT_SCORE * 0.20 +
        CLAIMS_HEALTH * 0.15 +
        PAYMENT_HEALTH * 0.20 +
        LOYALTY_SCORE * 0.15
    , 1) AS HEALTH_SCORE,
    -- Letter grade for business users
    CASE
        WHEN (RETENTION_SCORE * 0.30 + SENTIMENT_SCORE * 0.20 + CLAIMS_HEALTH * 0.15 + PAYMENT_HEALTH * 0.20 + LOYALTY_SCORE * 0.15) >= 85 THEN 'A'
        WHEN (RETENTION_SCORE * 0.30 + SENTIMENT_SCORE * 0.20 + CLAIMS_HEALTH * 0.15 + PAYMENT_HEALTH * 0.20 + LOYALTY_SCORE * 0.15) >= 70 THEN 'B'
        WHEN (RETENTION_SCORE * 0.30 + SENTIMENT_SCORE * 0.20 + CLAIMS_HEALTH * 0.15 + PAYMENT_HEALTH * 0.20 + LOYALTY_SCORE * 0.15) >= 55 THEN 'C'
        WHEN (RETENTION_SCORE * 0.30 + SENTIMENT_SCORE * 0.20 + CLAIMS_HEALTH * 0.15 + PAYMENT_HEALTH * 0.20 + LOYALTY_SCORE * 0.15) >= 40 THEN 'D'
        ELSE 'F'
    END AS HEALTH_GRADE
FROM scored;
