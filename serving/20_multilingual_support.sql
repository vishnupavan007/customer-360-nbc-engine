-- =============================================================================
-- 20_multilingual_support.sql - Cortex Translate for Multilingual Summaries
-- Enables customer summaries in any supported language using CORTEX.TRANSLATE
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE SCHEMA APP;
USE WAREHOUSE COMPUTE_WH;

-- =========================================================================
-- CUSTOMER_SUMMARY_TRANSLATED: Generate a customer summary in any language
-- Uses CORTEX.TRANSLATE to convert English customer intelligence summaries
-- into the target language (es=Spanish, fr=French, ja=Japanese, etc.)
-- =========================================================================
CREATE OR REPLACE FUNCTION CUSTOMER_SUMMARY_TRANSLATED(
    P_CUSTOMER_ID NUMBER, P_LANGUAGE VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
    SELECT SNOWFLAKE.CORTEX.TRANSLATE(
        'Customer: ' || c.FULL_NAME || ' (' || c.CUSTOMER_SEGMENT || '). ' ||
        'Churn Risk: ' || COALESCE(ROUND(cr.CHURN_RISK_SCORE, 2)::VARCHAR, 'N/A') || '. ' ||
        'Recommended Action: ' || COALESCE(n.ACTION_TYPE, 'None') || ' - ' ||
        COALESCE(n.ACTION_DESCRIPTION, 'No recommendation') || '. ' ||
        'Health Grade: ' || COALESCE(h.HEALTH_GRADE, 'N/A') ||
        ' (' || COALESCE(h.HEALTH_SCORE::VARCHAR, '0') || '/100).',
        'en',
        P_LANGUAGE
    )
    FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
    LEFT JOIN CUSTOMER_360.AI.DT_CHURN_RISK cr ON c.CUSTOMER_ID = cr.CUSTOMER_ID
    LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION n ON c.CUSTOMER_ID = n.CUSTOMER_ID
    LEFT JOIN CUSTOMER_360.AI.DT_CUSTOMER_HEALTH_SCORE h ON c.CUSTOMER_ID = h.CUSTOMER_ID
    WHERE c.CUSTOMER_ID = P_CUSTOMER_ID
    LIMIT 1
$$;
