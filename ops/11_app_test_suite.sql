-- =============================================================================
-- 11_app_test_suite.sql
-- One-click SQL test suite: validates every query the Streamlit app executes.
-- Run: CALL CUSTOMER_360.APP.RUN_APP_TESTS();
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE WAREHOUSE COMPUTE_WH;

-- The procedure is created with $$ delimiters so semicolons inside the body
-- do not conflict with the worksheet statement separator.

CREATE OR REPLACE PROCEDURE CUSTOMER_360.APP.RUN_APP_TESTS()
RETURNS TABLE(TEST_ID NUMBER, PAGE VARCHAR, TEST_NAME VARCHAR, STATUS VARCHAR, DETAIL VARCHAR, ROW_COUNT NUMBER)
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
    tid NUMBER DEFAULT 0;
    cnt NUMBER DEFAULT 0;
    val NUMBER DEFAULT 0;
BEGIN
    USE DATABASE CUSTOMER_360;
    USE WAREHOUSE COMPUTE_WH;
    CREATE OR REPLACE TEMPORARY TABLE _tr (TEST_ID NUMBER, PAGE VARCHAR, TEST_NAME VARCHAR, STATUS VARCHAR, DETAIL VARCHAR, ROW_COUNT NUMBER);

    -- Infrastructure
    tid := 1; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA IN ('RAW','CLEAN','CURATED','AI','APP') AND TABLE_TYPE='BASE TABLE';
    INSERT INTO _tr SELECT :tid, 'Infrastructure', 'All tables exist', CASE WHEN :cnt >= 17 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' tables (need >= 17)', :cnt;

    tid := 2; SHOW DYNAMIC TABLES IN DATABASE CUSTOMER_360; SELECT COUNT(*) INTO :cnt FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
    INSERT INTO _tr SELECT :tid, 'Infrastructure', 'Dynamic tables', CASE WHEN :cnt >= 9 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' DTs (need >= 9)', :cnt;

    tid := 3; SHOW CORTEX SEARCH SERVICES IN DATABASE CUSTOMER_360; SELECT COUNT(*) INTO :cnt FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
    INSERT INTO _tr SELECT :tid, 'Infrastructure', 'Cortex Search', CASE WHEN :cnt >= 1 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' service(s)', :cnt;

    tid := 4; SHOW SEMANTIC VIEWS IN SCHEMA CUSTOMER_360.APP; SELECT COUNT(*) INTO :cnt FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
    INSERT INTO _tr SELECT :tid, 'Infrastructure', 'Semantic view', CASE WHEN :cnt >= 1 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' view(s)', :cnt;

    -- Home page
    tid := 5; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED;
    INSERT INTO _tr SELECT :tid, 'Home', 'KPI: Total Customers', CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' customers', :cnt;

    tid := 6; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED WHERE IS_ACTIVE = TRUE;
    INSERT INTO _tr SELECT :tid, 'Home', 'KPI: Active Customers', CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' active', :cnt;

    tid := 7; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE >= 0.7;
    INSERT INTO _tr SELECT :tid, 'Home', 'KPI: High Churn Risk', 'PASS', :cnt || ' high-risk', :cnt;

    tid := 8; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE PRIORITY = 'High';
    INSERT INTO _tr SELECT :tid, 'Home', 'KPI: High Priority Actions', 'PASS', :cnt || ' actions', :cnt;

    tid := 9; SELECT COUNT(DISTINCT c.CUSTOMER_SEGMENT) INTO :cnt FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID=cr.CUSTOMER_ID WHERE cr.CHURN_RISK_SCORE IS NOT NULL;
    INSERT INTO _tr SELECT :tid, 'Home', 'Chart: Churn by Segment', CASE WHEN :cnt >= 3 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' segments', :cnt;

    tid := 10; SELECT COUNT(DISTINCT SENTIMENT_LABEL) INTO :cnt FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT;
    INSERT INTO _tr SELECT :tid, 'Home', 'Chart: Sentiment Dist', CASE WHEN :cnt >= 2 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' labels', :cnt;

    tid := 11; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE PRIORITY='High' AND ACTION_TYPE IS NOT NULL;
    INSERT INTO _tr SELECT :tid, 'Home', 'Table: Top Actions', CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' rows', :cnt;

    -- Customer 360 page
    tid := 12; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED WHERE FULL_NAME ILIKE '%smith%';
    INSERT INTO _tr SELECT :tid, 'Customer 360', 'Search: smith', CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' matches', :cnt;

    tid := 13; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.CLEAN.DT_CLAIMS;
    INSERT INTO _tr SELECT :tid, 'Customer 360', 'Claims data', CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' rows', :cnt;

    tid := 14; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.CLEAN.DT_LOANS;
    INSERT INTO _tr SELECT :tid, 'Customer 360', 'Loans data', CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' rows', :cnt;

    tid := 15; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.CURATED.CUSTOMER_INTERACTION_TIMELINE;
    INSERT INTO _tr SELECT :tid, 'Customer 360', 'Timeline data', CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' events', :cnt;

    -- Churn Risk page
    tid := 16; SELECT COUNT(DISTINCT CUSTOMER_SEGMENT) INTO :cnt FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE IS NOT NULL;
    INSERT INTO _tr SELECT :tid, 'Churn Risk', 'Segment filters', CASE WHEN :cnt >= 3 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' segments', :cnt;

    -- Sentiment page
    tid := 17; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT;
    INSERT INTO _tr SELECT :tid, 'Sentiment', 'Transcript data', CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' scored', :cnt;

    -- Next Best Action page
    tid := 18; SELECT COUNT(DISTINCT ACTION_TYPE) INTO :cnt FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION WHERE ACTION_TYPE IS NOT NULL;
    INSERT INTO _tr SELECT :tid, 'Next Best Action', 'Action types', CASE WHEN :cnt >= 3 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' types', :cnt;

    -- AI Advisor
    tid := 19; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED WHERE COMPLAINT_COUNT > 2;
    INSERT INTO _tr SELECT :tid, 'AI Advisor', 'Fallback: complaints', 'PASS', :cnt || ' with >2', :cnt;

    -- Operations
    tid := 20; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA IN ('RAW','CLEAN','CURATED','AI','APP') AND TABLE_TYPE='BASE TABLE';
    INSERT INTO _tr SELECT :tid, 'Operations', 'INFO_SCHEMA tables', CASE WHEN :cnt > 0 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' tables', :cnt;

    -- Data Quality
    tid := 21; SELECT ROUND(COUNT(CHURN_RISK_SCORE)*100.0/NULLIF(COUNT(*),0),1) INTO :val FROM CUSTOMER_360.AI.DT_CHURN_RISK;
    INSERT INTO _tr SELECT :tid, 'Data Quality', 'Churn completeness', CASE WHEN :val >= 90 THEN 'PASS' ELSE 'WARN' END, :val || '% non-null', :val;

    tid := 22; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.AI.DT_CHURN_RISK WHERE CHURN_RISK_SCORE < 0 OR CHURN_RISK_SCORE > 1;
    INSERT INTO _tr SELECT :tid, 'Data Quality', 'Churn range [0,1]', CASE WHEN :cnt=0 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' violations', :cnt;

    tid := 23; SELECT COUNT(*) INTO :cnt FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT WHERE SENTIMENT_SCORE < -1 OR SENTIMENT_SCORE > 1;
    INSERT INTO _tr SELECT :tid, 'Data Quality', 'Sentiment range [-1,1]', CASE WHEN :cnt=0 THEN 'PASS' ELSE 'FAIL' END, :cnt || ' violations', :cnt;

    LET rs RESULTSET := (SELECT * FROM _tr ORDER BY TEST_ID);
    RETURN TABLE(rs);
END;
$$;
