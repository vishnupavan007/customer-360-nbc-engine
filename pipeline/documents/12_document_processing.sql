-- =============================================================================
-- 12_document_processing.sql
-- Document AI: parse and extract structured fields from insurance documents
-- Uses AI_PARSE_DOCUMENT (full text/OCR) and AI_EXTRACT (structured fields)
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE WAREHOUSE COMPUTE_WH;

-- =========================================================================
-- Stage (already created, included here for completeness)
-- =========================================================================
CREATE STAGE IF NOT EXISTS CUSTOMER_360.RAW.DOCUMENT_STAGE
  DIRECTORY = (ENABLE = TRUE)
  COMMENT = 'Insurance claim forms and policy documents for AI extraction';

-- Refresh directory metadata
ALTER STAGE CUSTOMER_360.RAW.DOCUMENT_STAGE REFRESH;


-- =========================================================================
-- DT_DOCUMENT_PARSED - Full text extraction from each document
-- Uses AI_PARSE_DOCUMENT in LAYOUT mode for structured text extraction
-- =========================================================================
CREATE OR REPLACE DYNAMIC TABLE AI.DT_DOCUMENT_PARSED
  TARGET_LAG = '5 minutes'
  WAREHOUSE = COMPUTE_WH
AS
SELECT
    RELATIVE_PATH AS FILE_NAME,
    SIZE AS FILE_SIZE_BYTES,
    LAST_MODIFIED AS FILE_MODIFIED_AT,
    CASE
        WHEN RELATIVE_PATH ILIKE '%claim_form%' THEN 'Claim Form'
        WHEN RELATIVE_PATH ILIKE '%policy_summary%' THEN 'Policy Summary'
        ELSE 'Other'
    END AS DOCUMENT_TYPE,
    AI_PARSE_DOCUMENT(
        TO_FILE('@CUSTOMER_360.RAW.DOCUMENT_STAGE', RELATIVE_PATH),
        {'mode': 'LAYOUT'}
    ):content::VARCHAR AS PARSED_TEXT
FROM DIRECTORY(@CUSTOMER_360.RAW.DOCUMENT_STAGE)
WHERE RELATIVE_PATH ILIKE '%.txt' OR RELATIVE_PATH ILIKE '%.pdf';


-- =========================================================================
-- DT_DOCUMENT_EXTRACTED - Structured field extraction via AI_EXTRACT
-- Extracts claim/policy fields into JSON, then flattens to columns
-- =========================================================================
CREATE OR REPLACE DYNAMIC TABLE AI.DT_DOCUMENT_EXTRACTED
  TARGET_LAG = '5 minutes'
  WAREHOUSE = COMPUTE_WH
AS
WITH raw_extract AS (
    SELECT
        d.FILE_NAME,
        d.DOCUMENT_TYPE,
        d.FILE_SIZE_BYTES,
        d.FILE_MODIFIED_AT,
        d.PARSED_TEXT,
        AI_EXTRACT(
            TO_FILE('@CUSTOMER_360.RAW.DOCUMENT_STAGE', d.FILE_NAME),
            {
                'document_type': 'Type of document: Claim Form or Policy Summary',
                'reference_number': 'The main reference number (claim number or policy number)',
                'policy_number': 'The insurance policy number',
                'customer_name': 'Full name of the customer or policyholder',
                'customer_id': 'Customer ID number',
                'document_date': 'The primary date (date filed for claims, effective date for policies)',
                'amount': 'The primary dollar amount (claim amount or annual premium)',
                'category': 'The category or type (Auto, Home, Health, Life)',
                'status': 'Current status if mentioned',
                'description': 'Brief description or summary of the document contents'
            }
        ) AS EXTRACTED_RAW
    FROM AI.DT_DOCUMENT_PARSED d
)
SELECT
    FILE_NAME,
    DOCUMENT_TYPE,
    FILE_SIZE_BYTES,
    FILE_MODIFIED_AT,
    PARSED_TEXT,
    EXTRACTED_RAW:response:reference_number::VARCHAR AS REFERENCE_NUMBER,
    EXTRACTED_RAW:response:policy_number::VARCHAR AS POLICY_NUMBER,
    EXTRACTED_RAW:response:customer_name::VARCHAR AS CUSTOMER_NAME,
    EXTRACTED_RAW:response:customer_id::VARCHAR AS CUSTOMER_ID,
    EXTRACTED_RAW:response:document_date::VARCHAR AS DOCUMENT_DATE,
    EXTRACTED_RAW:response:amount::VARCHAR AS AMOUNT,
    EXTRACTED_RAW:response:category::VARCHAR AS CATEGORY,
    EXTRACTED_RAW:response:status::VARCHAR AS STATUS,
    EXTRACTED_RAW:response:description::VARCHAR AS DESCRIPTION,
    EXTRACTED_RAW:response:document_type::VARCHAR AS AI_DOCUMENT_TYPE
FROM raw_extract;
