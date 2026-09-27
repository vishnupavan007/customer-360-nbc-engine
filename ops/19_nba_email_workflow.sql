-- =============================================================================
-- 19_nba_email_workflow.sql - Automated NBA → Email Workflow
-- End-to-end automation: detect high-risk → generate NBA → draft email → notify
-- Uses CORTEX.COMPLETE to generate personalized retention emails
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE SCHEMA APP;
USE WAREHOUSE COMPUTE_WH;

-- =========================================================================
-- SP_SEND_NBA_EMAILS: Automated retention email campaign
--
-- Usage: CALL SP_SEND_NBA_EMAILS(0.6)  -- threshold: churn risk >= 0.6
--
-- Steps:
--   1. Finds top 10 high-risk customers with High priority NBA
--   2. Generates personalized retention emails via CORTEX.COMPLETE
--   3. Logs emails to NBA_EMAIL_LOG table
--   4. Sends summary notification to ops team
-- =========================================================================
CREATE OR REPLACE PROCEDURE SP_SEND_NBA_EMAILS(RISK_THRESHOLD FLOAT)
RETURNS TABLE(CUSTOMER_ID NUMBER, FULL_NAME VARCHAR, ACTION_TYPE VARCHAR, EMAIL_STATUS VARCHAR)
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
    rs RESULTSET;
BEGIN
    USE DATABASE CUSTOMER_360;

    CREATE OR REPLACE TEMPORARY TABLE _nba_emails AS
    SELECT
        n.CUSTOMER_ID,
        c.FULL_NAME,
        c.EMAIL,
        c.CUSTOMER_SEGMENT,
        n.ACTION_TYPE,
        n.ACTION_DESCRIPTION,
        ROUND(cr.CHURN_RISK_SCORE, 2) AS CHURN_RISK,
        SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b',
            'Write a brief, professional retention email (3-4 sentences) from SecureLife Insurance to ' ||
            c.FULL_NAME || ' (' || c.CUSTOMER_SEGMENT || ' customer). ' ||
            'Action: ' || n.ACTION_DESCRIPTION || '. ' ||
            'Tone: warm, proactive, personalized. Do not mention churn risk or internal scores. ' ||
            'Sign as: SecureLife Customer Success Team'
        ) AS EMAIL_BODY
    FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION n
    JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c ON c.CUSTOMER_ID = n.CUSTOMER_ID
    JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON cr.CUSTOMER_ID = n.CUSTOMER_ID
    WHERE cr.CHURN_RISK_SCORE >= :RISK_THRESHOLD
      AND n.PRIORITY = 'High'
    ORDER BY cr.CHURN_RISK_SCORE DESC
    LIMIT 10;

    -- Log for audit and review
    CREATE OR REPLACE TABLE CUSTOMER_360.APP.NBA_EMAIL_LOG AS
    SELECT CUSTOMER_ID, FULL_NAME, EMAIL, CUSTOMER_SEGMENT,
           ACTION_TYPE, CHURN_RISK, LEFT(EMAIL_BODY, 1000) AS EMAIL_BODY,
           CURRENT_TIMESTAMP() AS GENERATED_AT, 'DRAFTED' AS STATUS
    FROM _nba_emails;

    -- Notify ops team
    CALL SYSTEM$SEND_EMAIL(
        'customer_360_notifications',
        'suresh.erragana@gmail.com',
        'NBA Campaign: retention emails drafted',
        (SELECT LISTAGG(FULL_NAME || ' - Churn: ' || CHURN_RISK::VARCHAR || ' - ' || ACTION_TYPE, '\n')
            WITHIN GROUP (ORDER BY CHURN_RISK DESC)
         FROM _nba_emails)
    );

    rs := (SELECT CUSTOMER_ID, FULL_NAME, ACTION_TYPE, STATUS AS EMAIL_STATUS
           FROM CUSTOMER_360.APP.NBA_EMAIL_LOG);
    RETURN TABLE(rs);
END;
$$;
