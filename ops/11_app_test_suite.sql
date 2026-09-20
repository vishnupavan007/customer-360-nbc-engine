-- =============================================================================
-- 11_app_test_suite.sql
-- One-click test suite: validates every query the Streamlit app executes.
-- Run: CALL CUSTOMER_360.APP.RUN_APP_TESTS();
-- Returns a single result set with PASS/FAIL per test.
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE WAREHOUSE COMPUTE_WH;

CREATE OR REPLACE PROCEDURE CUSTOMER_360.APP.RUN_APP_TESTS()
RETURNS TABLE(
    TEST_ID     NUMBER,
    PAGE        VARCHAR,
    TEST_NAME   VARCHAR,
    STATUS      VARCHAR,
    DETAIL      VARCHAR,
    ROW_COUNT   NUMBER,
    DURATION_MS NUMBER
)
LANGUAGE SQL
AS
BEGIN
    -- Results accumulator
    CREATE OR REPLACE TEMPORARY TABLE _test_results (
        TEST_ID     NUMBER,
        PAGE        VARCHAR,
        TEST_NAME   VARCHAR,
        STATUS      VARCHAR,
        DETAIL      VARCHAR,
        ROW_COUNT   NUMBER,
        DURATION_MS NUMBER
    );

    LET :tid NUMBER := 0;
    LET :t0 TIMESTAMP_NTZ;
    LET :t1 TIMESTAMP_NTZ;
    LET :cnt NUMBER;
    LET :val VARCHAR;

    -- =====================================================================
    -- INFRASTRUCTURE: Tables, schemas, objects exist
    -- =====================================================================

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA IN ('RAW','CLEAN','CURATED','AI','APP')
          AND TABLE_TYPE = 'BASE TABLE';
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Infrastructure', 'All tables exist (RAW+CLEAN+CURATED+AI)',
            CASE WHEN :cnt >= 17 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' tables found (expected >= 17)',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Infrastructure', 'All tables exist', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt FROM (SHOW DYNAMIC TABLES IN DATABASE CUSTOMER_360);
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Infrastructure', 'Dynamic tables active',
            CASE WHEN :cnt >= 9 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' dynamic tables (expected >= 9)',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Infrastructure', 'Dynamic tables active', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt FROM (SHOW CORTEX SEARCH SERVICES IN DATABASE CUSTOMER_360);
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Infrastructure', 'Cortex Search Service exists',
            CASE WHEN :cnt >= 1 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' search service(s)',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Infrastructure', 'Cortex Search Service exists', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt FROM (SHOW SEMANTIC VIEWS IN SCHEMA CUSTOMER_360.APP);
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Infrastructure', 'Semantic view exists',
            CASE WHEN :cnt >= 1 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' semantic view(s)',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Infrastructure', 'Semantic view exists', 'FAIL', SQLERRM, 0, 0);
    END;

    -- =====================================================================
    -- HOME PAGE (app.py): KPIs + charts + action table
    -- =====================================================================

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Home', 'KPI: Total Customers',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' customers',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Home', 'KPI: Total Customers', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED WHERE IS_ACTIVE = TRUE;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Home', 'KPI: Active Customers',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' active',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Home', 'KPI: Active Customers', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE >= 0.7;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Home', 'KPI: High Churn Risk (>=0.7)',
            'PASS',
            :cnt || ' high-risk customers',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Home', 'KPI: High Churn Risk', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE PRIORITY = 'High';
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Home', 'KPI: High Priority Actions',
            'PASS',
            :cnt || ' high-priority actions',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Home', 'KPI: High Priority Actions', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM (
            SELECT c.CUSTOMER_SEGMENT, ROUND(AVG(cr.CHURN_RISK_SCORE), 3) AS AVG_CHURN_RISK
            FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
            JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID = cr.CUSTOMER_ID
            WHERE cr.CHURN_RISK_SCORE IS NOT NULL
            GROUP BY c.CUSTOMER_SEGMENT
        );
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Home', 'Chart: Churn Risk by Segment',
            CASE WHEN :cnt >= 3 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' segments returned',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Home', 'Chart: Churn Risk by Segment', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM (
            SELECT SENTIMENT_LABEL, COUNT(*) AS CALL_COUNT
            FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
            GROUP BY SENTIMENT_LABEL
        );
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Home', 'Chart: Sentiment Distribution',
            CASE WHEN :cnt >= 2 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' sentiment labels',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Home', 'Chart: Sentiment Distribution', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM (
            SELECT nba.FULL_NAME, nba.CUSTOMER_SEGMENT,
                   ROUND(nba.CHURN_RISK_SCORE, 2) AS CHURN_RISK,
                   nba.ACTION_TYPE, nba.ACTION_DESCRIPTION,
                   nba.PRIORITY, nba.RECOMMENDED_CHANNEL
            FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba
            WHERE nba.PRIORITY = 'High' AND nba.ACTION_TYPE IS NOT NULL
            ORDER BY nba.CHURN_RISK_SCORE DESC
            LIMIT 15
        );
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Home', 'Table: Top Action Items',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' rows returned',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Home', 'Table: Top Action Items', 'FAIL', SQLERRM, 0, 0);
    END;

    -- =====================================================================
    -- CUSTOMER 360 PAGE (1_Customer_360.py): search + detail queries
    -- =====================================================================

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED
        WHERE CUSTOMER_SEGMENT IS NOT NULL;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Customer 360', 'Segments overview query',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' customers with segments',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Customer 360', 'Segments overview query', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM (
            SELECT c.CUSTOMER_ID, c.FULL_NAME, c.CUSTOMER_SEGMENT,
                   cr.CHURN_RISK_SCORE, cr.RETENTION_URGENCY,
                   nba.ACTION_TYPE, nba.PRIORITY
            FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
            LEFT JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID = cr.CUSTOMER_ID
            LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba ON c.CUSTOMER_ID = nba.CUSTOMER_ID
            WHERE c.FULL_NAME ILIKE '%smith%'
        );
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Customer 360', 'Customer search (ILIKE smith)',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' matches found',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Customer 360', 'Customer search (ILIKE)', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.CLEAN.DT_CLAIMS;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Customer 360', 'Claims data available',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' claims',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Customer 360', 'Claims data available', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.CLEAN.DT_LOANS;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Customer 360', 'Loans data available',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' loans',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Customer 360', 'Loans data available', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.CURATED.CUSTOMER_INTERACTION_TIMELINE;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Customer 360', 'Interaction timeline data',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' timeline events',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Customer 360', 'Interaction timeline', 'FAIL', SQLERRM, 0, 0);
    END;

    -- =====================================================================
    -- CHURN RISK PAGE (2_Churn_Risk.py): segments, filters, table
    -- =====================================================================

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(DISTINCT CUSTOMER_SEGMENT) INTO :cnt
        FROM CUSTOMER_360.AI.DT_CHURN_RISK
        WHERE CHURN_RISK_SCORE IS NOT NULL;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Churn Risk', 'Segment filter values',
            CASE WHEN :cnt >= 3 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' distinct segments',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Churn Risk', 'Segment filter values', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM (
            SELECT CUSTOMER_SEGMENT, ROUND(AVG(CHURN_RISK_SCORE),3) AS AVG_RISK, COUNT(*) AS CUSTOMERS
            FROM CUSTOMER_360.AI.DT_CHURN_RISK
            WHERE CHURN_RISK_SCORE IS NOT NULL
            GROUP BY CUSTOMER_SEGMENT
        );
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Churn Risk', 'Avg risk by segment query',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' segment groups',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Churn Risk', 'Avg risk by segment', 'FAIL', SQLERRM, 0, 0);
    END;

    -- =====================================================================
    -- SENTIMENT PAGE (3_Sentiment.py): charts, agent table, transcript
    -- =====================================================================

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Sentiment', 'Transcript sentiment data',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' transcripts scored',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Sentiment', 'Transcript sentiment data', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM (
            SELECT CALL_REASON, SENTIMENT_LABEL, COUNT(*) AS CNT
            FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
            GROUP BY CALL_REASON, SENTIMENT_LABEL
        );
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Sentiment', 'Sentiment by call reason query',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' reason-label groups',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Sentiment', 'Sentiment by call reason', 'FAIL', SQLERRM, 0, 0);
    END;

    -- =====================================================================
    -- NEXT BEST ACTION PAGE (4_Next_Best_Action.py): filters, table
    -- =====================================================================

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(DISTINCT ACTION_TYPE) INTO :cnt
        FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
        WHERE ACTION_TYPE IS NOT NULL;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Next Best Action', 'Distinct action types',
            CASE WHEN :cnt >= 3 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' action types',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Next Best Action', 'Distinct action types', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(DISTINCT PRIORITY) INTO :cnt
        FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
        WHERE PRIORITY IS NOT NULL;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Next Best Action', 'Distinct priority levels',
            CASE WHEN :cnt >= 2 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' priority levels',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Next Best Action', 'Distinct priority levels', 'FAIL', SQLERRM, 0, 0);
    END;

    -- =====================================================================
    -- AI ADVISOR PAGE (5_AI_Advisor.py): SQL fallback queries
    -- =====================================================================

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM (
            SELECT cr.FULL_NAME, cr.CUSTOMER_SEGMENT, ROUND(cr.CHURN_RISK_SCORE,3) AS CHURN_RISK,
                   cr.RETENTION_URGENCY, nba.ACTION_TYPE, nba.PRIORITY
            FROM CUSTOMER_360.AI.DT_CHURN_RISK cr
            LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba ON cr.CUSTOMER_ID=nba.CUSTOMER_ID
            WHERE cr.CHURN_RISK_SCORE IS NOT NULL ORDER BY cr.CHURN_RISK_SCORE DESC LIMIT 10
        );
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'AI Advisor', 'Fallback: top churn risk query',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' rows',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'AI Advisor', 'Fallback: top churn risk', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM (
            SELECT c.CUSTOMER_SEGMENT, ROUND(AVG(s.SENTIMENT_SCORE),3) AS AVG_SENTIMENT, COUNT(*) AS CALLS
            FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
            JOIN CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT s ON c.CUSTOMER_ID=s.CUSTOMER_ID
            GROUP BY c.CUSTOMER_SEGMENT
        );
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'AI Advisor', 'Fallback: sentiment by segment',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' segments',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'AI Advisor', 'Fallback: sentiment by segment', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED
        WHERE COMPLAINT_COUNT > 2;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'AI Advisor', 'Fallback: complaint count query',
            'PASS',
            :cnt || ' customers with >2 complaints',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'AI Advisor', 'Fallback: complaint count', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM (
            SELECT nba.ACTION_TYPE, COUNT(*) AS ACTION_COUNT
            FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION nba
            WHERE nba.LATEST_SENTIMENT_LABEL = 'Negative' AND nba.ACTION_TYPE IS NOT NULL
            GROUP BY nba.ACTION_TYPE
        );
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'AI Advisor', 'Fallback: NBA for negative sentiment',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' action types',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'AI Advisor', 'Fallback: NBA negative sentiment', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        LET :resp VARCHAR;
        SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b', 'Reply with: test passed') INTO :resp;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'AI Advisor', 'Cortex COMPLETE (llama3.1-8b)',
            CASE WHEN :resp IS NOT NULL AND LENGTH(:resp) > 0 THEN 'PASS' ELSE 'FAIL' END,
            'Response length: ' || LENGTH(:resp),
            1, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'AI Advisor', 'Cortex COMPLETE (llama3.1-8b)', 'FAIL', SQLERRM, 0, 0);
    END;

    -- =====================================================================
    -- OPERATIONS PAGE (6_Operations.py): INFORMATION_SCHEMA, DT health
    -- =====================================================================

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA IN ('RAW','CLEAN','CURATED','AI','APP')
          AND TABLE_TYPE = 'BASE TABLE';
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Operations', 'INFORMATION_SCHEMA table counts',
            CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' tables in scope',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Operations', 'INFORMATION_SCHEMA table counts', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM TABLE(CUSTOMER_360.INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
            NAME_PREFIX => 'CUSTOMER_360.'
        ))
        WHERE REFRESH_START_TIME >= DATEADD('hour', -24, CURRENT_TIMESTAMP())
          AND SCHEMA_NAME IN ('CLEAN','CURATED','AI');
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Operations', 'DT refresh history (24h)',
            'PASS',
            :cnt || ' refreshes in last 24h',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Operations', 'DT refresh history (24h)', 'FAIL', SQLERRM, 0, 0);
    END;

    -- =====================================================================
    -- DATA QUALITY: NULL rates, value ranges, referential integrity
    -- =====================================================================

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT ROUND(COUNT(CHURN_RISK_SCORE) * 100.0 / NULLIF(COUNT(*), 0), 1) INTO :val
        FROM CUSTOMER_360.AI.DT_CHURN_RISK;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Data Quality', 'Churn risk completeness',
            CASE WHEN :val::FLOAT >= 90 THEN 'PASS' ELSE 'WARN' END,
            :val || '% non-null churn scores',
            :val::NUMBER, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Data Quality', 'Churn risk completeness', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT ROUND(COUNT(ACTION_TYPE) * 100.0 / NULLIF(COUNT(*), 0), 1) INTO :val
        FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Data Quality', 'NBA completeness',
            CASE WHEN :val::FLOAT >= 90 THEN 'PASS' ELSE 'WARN' END,
            :val || '% non-null action types',
            :val::NUMBER, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Data Quality', 'NBA completeness', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM CUSTOMER_360.AI.DT_CHURN_RISK
        WHERE CHURN_RISK_SCORE < 0 OR CHURN_RISK_SCORE > 1;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Data Quality', 'Churn score range [0,1]',
            CASE WHEN :cnt = 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' out-of-range scores',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Data Quality', 'Churn score range [0,1]', 'FAIL', SQLERRM, 0, 0);
    END;

    :tid := :tid + 1;
    :t0 := CURRENT_TIMESTAMP();
    BEGIN
        SELECT COUNT(*) INTO :cnt
        FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
        WHERE SENTIMENT_SCORE < -1 OR SENTIMENT_SCORE > 1;
        :t1 := CURRENT_TIMESTAMP();
        INSERT INTO _test_results VALUES (
            :tid, 'Data Quality', 'Sentiment score range [-1,1]',
            CASE WHEN :cnt = 0 THEN 'PASS' ELSE 'FAIL' END,
            :cnt || ' out-of-range scores',
            :cnt, TIMESTAMPDIFF(MILLISECOND, :t0, :t1)
        );
    EXCEPTION WHEN OTHER THEN
        INSERT INTO _test_results VALUES (:tid, 'Data Quality', 'Sentiment score range [-1,1]', 'FAIL', SQLERRM, 0, 0);
    END;

    -- =====================================================================
    -- Return results
    -- =====================================================================
    LET rs RESULTSET := (
        SELECT * FROM _test_results ORDER BY TEST_ID
    );
    RETURN TABLE(rs);
END;
