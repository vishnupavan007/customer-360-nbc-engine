-- =============================================================================
-- 21_ai_evaluation_harness.sql - AI Model Quality Evaluation
-- Comprehensive test suite for all AI/LLM model outputs
-- Tests: parse success, value ranges, consistency, cross-references, coverage
-- Usage: CALL CUSTOMER_360.APP.RUN_AI_EVALUATION()
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE SCHEMA APP;
USE WAREHOUSE COMPUTE_WH;

CREATE OR REPLACE PROCEDURE RUN_AI_EVALUATION()
RETURNS TABLE(TEST_ID NUMBER, MODEL VARCHAR, TEST_NAME VARCHAR, STATUS VARCHAR, DETAIL VARCHAR, METRIC NUMBER)
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
    rs RESULTSET;
BEGIN
    USE DATABASE CUSTOMER_360;

    CREATE OR REPLACE TEMPORARY TABLE _ai_results (
        TEST_ID NUMBER, MODEL VARCHAR, TEST_NAME VARCHAR, STATUS VARCHAR, DETAIL VARCHAR, METRIC NUMBER
    );

    -- ============================================================
    -- CHURN RISK MODEL (6 tests)
    -- ============================================================

    -- Test 1: JSON parse success rate (>= 95% threshold)
    INSERT INTO _ai_results
    SELECT 1, 'Churn Risk', 'Parse success rate',
        CASE WHEN ROUND(100.0 * COUNT_IF(CHURN_RISK_SCORE IS NOT NULL) / COUNT(*), 1) >= 95 THEN 'PASS' ELSE 'FAIL' END,
        ROUND(100.0 * COUNT_IF(CHURN_RISK_SCORE IS NOT NULL) / COUNT(*), 1)::VARCHAR || '% parsed',
        ROUND(100.0 * COUNT_IF(CHURN_RISK_SCORE IS NOT NULL) / COUNT(*), 1)
    FROM AI.DT_CHURN_RISK;

    -- Test 2: Score range [0, 1]
    INSERT INTO _ai_results
    SELECT 2, 'Churn Risk', 'Score range [0,1]',
        CASE WHEN COUNT_IF(CHURN_RISK_SCORE < 0 OR CHURN_RISK_SCORE > 1) = 0 THEN 'PASS' ELSE 'FAIL' END,
        COUNT_IF(CHURN_RISK_SCORE < 0 OR CHURN_RISK_SCORE > 1)::VARCHAR || ' violations',
        COUNT_IF(CHURN_RISK_SCORE < 0 OR CHURN_RISK_SCORE > 1)
    FROM AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE IS NOT NULL;

    -- Test 3: Retention urgency enum validity
    INSERT INTO _ai_results
    SELECT 3, 'Churn Risk', 'Valid retention urgency',
        CASE WHEN COUNT_IF(RETENTION_URGENCY NOT IN ('Critical','High','Medium','Low')) = 0 THEN 'PASS' ELSE 'FAIL' END,
        COUNT_IF(RETENTION_URGENCY NOT IN ('Critical','High','Medium','Low'))::VARCHAR || ' invalid',
        COUNT_IF(RETENTION_URGENCY NOT IN ('Critical','High','Medium','Low'))
    FROM AI.DT_CHURN_RISK WHERE RETENTION_URGENCY IS NOT NULL;

    -- Test 4: Score-urgency correlation (high risk => Critical/High)
    INSERT INTO _ai_results
    SELECT 4, 'Churn Risk', 'Score-urgency correlation',
        CASE WHEN corr >= 70 THEN 'PASS' ELSE 'WARN' END,
        corr::VARCHAR || '% correlation',
        corr
    FROM (SELECT ROUND(100.0 * COUNT_IF(RETENTION_URGENCY IN ('Critical','High')) / NULLIF(COUNT(*), 0), 1) AS corr
          FROM AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE >= 0.7);

    -- Test 5: Confidence scores populated
    INSERT INTO _ai_results
    SELECT 5, 'Churn Risk', 'Confidence populated',
        CASE WHEN ROUND(100.0 * COUNT_IF(MODEL_CONFIDENCE IS NOT NULL) / COUNT(*), 1) >= 90 THEN 'PASS' ELSE 'FAIL' END,
        ROUND(100.0 * COUNT_IF(MODEL_CONFIDENCE IS NOT NULL) / COUNT(*), 1)::VARCHAR || '%',
        ROUND(100.0 * COUNT_IF(MODEL_CONFIDENCE IS NOT NULL) / COUNT(*), 1)
    FROM AI.DT_CHURN_RISK;

    -- Test 6: Risk factors array populated
    INSERT INTO _ai_results
    SELECT 6, 'Churn Risk', 'Risk factors populated',
        CASE WHEN ROUND(100.0 * COUNT_IF(RISK_FACTORS IS NOT NULL) / COUNT(*), 1) >= 90 THEN 'PASS' ELSE 'FAIL' END,
        ROUND(100.0 * COUNT_IF(RISK_FACTORS IS NOT NULL) / COUNT(*), 1)::VARCHAR || '%',
        ROUND(100.0 * COUNT_IF(RISK_FACTORS IS NOT NULL) / COUNT(*), 1)
    FROM AI.DT_CHURN_RISK;

    -- ============================================================
    -- NEXT BEST ACTION MODEL (4 tests)
    -- ============================================================

    INSERT INTO _ai_results
    SELECT 7, 'Next Best Action', 'Parse success rate',
        CASE WHEN ROUND(100.0 * COUNT_IF(ACTION_TYPE IS NOT NULL) / COUNT(*), 1) >= 95 THEN 'PASS' ELSE 'FAIL' END,
        ROUND(100.0 * COUNT_IF(ACTION_TYPE IS NOT NULL) / COUNT(*), 1)::VARCHAR || '%',
        ROUND(100.0 * COUNT_IF(ACTION_TYPE IS NOT NULL) / COUNT(*), 1)
    FROM AI.DT_NEXT_BEST_ACTION;

    INSERT INTO _ai_results
    SELECT 8, 'Next Best Action', 'Valid action types (3-10 distinct)',
        CASE WHEN COUNT(DISTINCT ACTION_TYPE) BETWEEN 3 AND 10 THEN 'PASS' ELSE 'WARN' END,
        COUNT(DISTINCT ACTION_TYPE)::VARCHAR || ' types',
        COUNT(DISTINCT ACTION_TYPE)
    FROM AI.DT_NEXT_BEST_ACTION WHERE ACTION_TYPE IS NOT NULL;

    INSERT INTO _ai_results
    SELECT 9, 'Next Best Action', 'Valid priority values',
        CASE WHEN COUNT_IF(PRIORITY NOT IN ('High','Medium','Low')) = 0 THEN 'PASS' ELSE 'FAIL' END,
        COUNT_IF(PRIORITY NOT IN ('High','Medium','Low'))::VARCHAR || ' invalid',
        COUNT_IF(PRIORITY NOT IN ('High','Medium','Low'))
    FROM AI.DT_NEXT_BEST_ACTION WHERE PRIORITY IS NOT NULL;

    INSERT INTO _ai_results
    SELECT 10, 'Next Best Action', 'Descriptions meaningful (>10 chars)',
        CASE WHEN ROUND(100.0 * COUNT_IF(LENGTH(TRIM(ACTION_DESCRIPTION)) > 10) / COUNT(*), 1) >= 90 THEN 'PASS' ELSE 'FAIL' END,
        ROUND(100.0 * COUNT_IF(LENGTH(TRIM(ACTION_DESCRIPTION)) > 10) / COUNT(*), 1)::VARCHAR || '%',
        ROUND(100.0 * COUNT_IF(LENGTH(TRIM(ACTION_DESCRIPTION)) > 10) / COUNT(*), 1)
    FROM AI.DT_NEXT_BEST_ACTION WHERE ACTION_DESCRIPTION IS NOT NULL;

    -- ============================================================
    -- SENTIMENT MODEL (3 tests)
    -- ============================================================

    INSERT INTO _ai_results
    SELECT 11, 'Sentiment', 'Score range [-1,1]',
        CASE WHEN COUNT_IF(SENTIMENT_SCORE < -1 OR SENTIMENT_SCORE > 1) = 0 THEN 'PASS' ELSE 'FAIL' END,
        COUNT_IF(SENTIMENT_SCORE < -1 OR SENTIMENT_SCORE > 1)::VARCHAR || ' violations',
        COUNT_IF(SENTIMENT_SCORE < -1 OR SENTIMENT_SCORE > 1)
    FROM AI.DT_TRANSCRIPT_SENTIMENT;

    INSERT INTO _ai_results
    SELECT 12, 'Sentiment', 'Label-score consistency',
        CASE WHEN mismatch <= 5 THEN 'PASS' ELSE 'FAIL' END,
        mismatch::VARCHAR || '% mismatches', mismatch
    FROM (SELECT ROUND(100.0 * COUNT_IF(
            (SENTIMENT_LABEL = 'Positive' AND SENTIMENT_SCORE < 0.3) OR
            (SENTIMENT_LABEL = 'Negative' AND SENTIMENT_SCORE > -0.3)
        ) / NULLIF(COUNT(*), 0), 1) AS mismatch FROM AI.DT_TRANSCRIPT_SENTIMENT);

    INSERT INTO _ai_results
    SELECT 13, 'Sentiment', 'Summaries populated (>20 chars)',
        CASE WHEN ROUND(100.0 * COUNT_IF(LENGTH(TRIM(CALL_SUMMARY)) > 20) / COUNT(*), 1) >= 90 THEN 'PASS' ELSE 'FAIL' END,
        ROUND(100.0 * COUNT_IF(LENGTH(TRIM(CALL_SUMMARY)) > 20) / COUNT(*), 1)::VARCHAR || '%',
        ROUND(100.0 * COUNT_IF(LENGTH(TRIM(CALL_SUMMARY)) > 20) / COUNT(*), 1)
    FROM AI.DT_TRANSCRIPT_SENTIMENT;

    -- ============================================================
    -- DOCUMENT EXTRACTION (3 tests)
    -- ============================================================

    INSERT INTO _ai_results
    SELECT 14, 'Document Extraction', 'Extraction completeness',
        CASE WHEN COUNT(*) >= 20 THEN 'PASS' ELSE 'FAIL' END,
        COUNT(*)::VARCHAR || ' documents', COUNT(*)
    FROM AI.DT_DOCUMENT_EXTRACTED;

    INSERT INTO _ai_results
    SELECT 15, 'Document Extraction', 'Reference numbers populated',
        CASE WHEN ROUND(100.0 * COUNT_IF(REFERENCE_NUMBER IS NOT NULL) / COUNT(*), 1) >= 80 THEN 'PASS' ELSE 'FAIL' END,
        ROUND(100.0 * COUNT_IF(REFERENCE_NUMBER IS NOT NULL) / COUNT(*), 1)::VARCHAR || '%',
        ROUND(100.0 * COUNT_IF(REFERENCE_NUMBER IS NOT NULL) / COUNT(*), 1)
    FROM AI.DT_DOCUMENT_EXTRACTED;

    INSERT INTO _ai_results
    SELECT 16, 'Document Extraction', 'Customer cross-reference match',
        CASE WHEN matched >= 8 THEN 'PASS' ELSE 'WARN' END,
        matched::VARCHAR || '/' || total::VARCHAR || ' matched', matched
    FROM (SELECT COUNT(*) AS total,
            COUNT_IF(TRY_CAST(d.CUSTOMER_ID AS NUMBER) IN (SELECT CUSTOMER_ID FROM CURATED.CUSTOMER_360_UNIFIED)) AS matched
          FROM AI.DT_DOCUMENT_EXTRACTED d);

    -- ============================================================
    -- HEALTH SCORE (4 tests)
    -- ============================================================

    INSERT INTO _ai_results
    SELECT 17, 'Health Score', 'Coverage (>= 1900 customers)',
        CASE WHEN COUNT(*) >= 1900 THEN 'PASS' ELSE 'FAIL' END,
        COUNT(*)::VARCHAR || ' scored', COUNT(*)
    FROM AI.DT_CUSTOMER_HEALTH_SCORE;

    INSERT INTO _ai_results
    SELECT 18, 'Health Score', 'Score range [0,100]',
        CASE WHEN COUNT_IF(HEALTH_SCORE < 0 OR HEALTH_SCORE > 100) = 0 THEN 'PASS' ELSE 'FAIL' END,
        COUNT_IF(HEALTH_SCORE < 0 OR HEALTH_SCORE > 100)::VARCHAR || ' violations',
        COUNT_IF(HEALTH_SCORE < 0 OR HEALTH_SCORE > 100)
    FROM AI.DT_CUSTOMER_HEALTH_SCORE;

    INSERT INTO _ai_results
    SELECT 19, 'Health Score', 'All 5 grades present',
        CASE WHEN COUNT(DISTINCT HEALTH_GRADE) = 5 THEN 'PASS' ELSE 'WARN' END,
        COUNT(DISTINCT HEALTH_GRADE)::VARCHAR || ' grades',
        COUNT(DISTINCT HEALTH_GRADE)
    FROM AI.DT_CUSTOMER_HEALTH_SCORE;

    INSERT INTO _ai_results
    SELECT 20, 'Health Score', 'Grade-score alignment',
        CASE WHEN COUNT_IF((HEALTH_GRADE='A' AND HEALTH_SCORE<85) OR (HEALTH_GRADE='F' AND HEALTH_SCORE>=40)) = 0 THEN 'PASS' ELSE 'FAIL' END,
        COUNT_IF((HEALTH_GRADE='A' AND HEALTH_SCORE<85) OR (HEALTH_GRADE='F' AND HEALTH_SCORE>=40))::VARCHAR || ' misaligned',
        COUNT_IF((HEALTH_GRADE='A' AND HEALTH_SCORE<85) OR (HEALTH_GRADE='F' AND HEALTH_SCORE>=40))
    FROM AI.DT_CUSTOMER_HEALTH_SCORE;

    rs := (SELECT * FROM _ai_results ORDER BY TEST_ID);
    RETURN TABLE(rs);
END;
$$;
