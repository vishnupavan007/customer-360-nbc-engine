-- =============================================================================
-- 12_document_processing.sql
-- Document AI: structured field extraction from insurance documents
-- Sources from RAW.RAW_DOCUMENTS (same pattern as call transcripts)
-- Uses SNOWFLAKE.CORTEX.COMPLETE for structured extraction from text content
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE WAREHOUSE COMPUTE_WH;

-- =========================================================================
-- DT_DOCUMENT_PARSED - Cleaned document content from RAW layer
-- Mirrors how DT_CALL_TRANSCRIPTS sources from RAW_CALL_TRANSCRIPTS
-- =========================================================================
CREATE OR REPLACE DYNAMIC TABLE AI.DT_DOCUMENT_PARSED
  TARGET_LAG = '5 minutes'
  WAREHOUSE = COMPUTE_WH
AS
SELECT
    DOCUMENT_ID,
    CUSTOMER_ID,
    FILE_NAME,
    DOCUMENT_TYPE,
    FILE_SIZE_BYTES,
    CREATED_AT AS FILE_MODIFIED_AT,
    DOCUMENT_TEXT AS PARSED_TEXT
FROM RAW.RAW_DOCUMENTS
WHERE DOCUMENT_TEXT IS NOT NULL AND LENGTH(TRIM(DOCUMENT_TEXT)) > 0
QUALIFY ROW_NUMBER() OVER (PARTITION BY DOCUMENT_ID ORDER BY CREATED_AT DESC) = 1;


-- =========================================================================
-- DT_DOCUMENT_EXTRACTED - AI-powered structured field extraction
-- Uses CORTEX.COMPLETE to extract structured fields from document text,
-- analogous to how DT_CHURN_RISK uses CORTEX.COMPLETE for risk scoring
-- =========================================================================
CREATE OR REPLACE DYNAMIC TABLE AI.DT_DOCUMENT_EXTRACTED
  TARGET_LAG = '5 minutes'
  WAREHOUSE = COMPUTE_WH
AS
SELECT
    d.DOCUMENT_ID,
    d.FILE_NAME,
    d.DOCUMENT_TYPE,
    d.FILE_SIZE_BYTES,
    d.FILE_MODIFIED_AT,
    d.CUSTOMER_ID AS SOURCE_CUSTOMER_ID,
    d.PARSED_TEXT,
    SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b',
        'You are a document data extraction specialist. ' ||
        'Extract structured fields from this insurance document and return ONLY a valid JSON object with these exact keys: ' ||
        'reference_number (the main reference number — claim number or policy number), ' ||
        'policy_number (the insurance policy number), ' ||
        'customer_name (full name of the customer or policyholder), ' ||
        'customer_id (customer ID number as a string), ' ||
        'document_date (the primary date — date filed for claims, effective date for policies, format YYYY-MM-DD), ' ||
        'amount (the primary dollar amount — claim amount or annual premium, as a number without $ sign), ' ||
        'category (Auto, Home, Health, Life, Travel, or Other), ' ||
        'status (current status if mentioned), ' ||
        'description (1-2 sentence summary of the document). ' ||
        'Document text: ' || LEFT(d.PARSED_TEXT, 3000)
    ) AS EXTRACT_RAW,
    TRY_PARSE_JSON(REGEXP_SUBSTR(EXTRACT_RAW, '\\{[\\s\\S]*\\}')):reference_number::VARCHAR AS REFERENCE_NUMBER,
    TRY_PARSE_JSON(REGEXP_SUBSTR(EXTRACT_RAW, '\\{[\\s\\S]*\\}')):policy_number::VARCHAR AS POLICY_NUMBER,
    TRY_PARSE_JSON(REGEXP_SUBSTR(EXTRACT_RAW, '\\{[\\s\\S]*\\}')):customer_name::VARCHAR AS CUSTOMER_NAME,
    TRY_PARSE_JSON(REGEXP_SUBSTR(EXTRACT_RAW, '\\{[\\s\\S]*\\}')):customer_id::VARCHAR AS CUSTOMER_ID,
    TRY_PARSE_JSON(REGEXP_SUBSTR(EXTRACT_RAW, '\\{[\\s\\S]*\\}')):document_date::VARCHAR AS DOCUMENT_DATE,
    TRY_PARSE_JSON(REGEXP_SUBSTR(EXTRACT_RAW, '\\{[\\s\\S]*\\}')):amount::VARCHAR AS AMOUNT,
    TRY_PARSE_JSON(REGEXP_SUBSTR(EXTRACT_RAW, '\\{[\\s\\S]*\\}')):category::VARCHAR AS CATEGORY,
    TRY_PARSE_JSON(REGEXP_SUBSTR(EXTRACT_RAW, '\\{[\\s\\S]*\\}')):status::VARCHAR AS STATUS,
    TRY_PARSE_JSON(REGEXP_SUBSTR(EXTRACT_RAW, '\\{[\\s\\S]*\\}')):description::VARCHAR AS DESCRIPTION
FROM AI.DT_DOCUMENT_PARSED d;
