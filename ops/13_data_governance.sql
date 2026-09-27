-- =============================================================================
-- 13_data_governance.sql
-- Data governance for Customer 360: masking policies, object tags, and
-- their application to PII columns and tables.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Masking Policies
--    Privileged roles (ACCOUNTADMIN, SYSADMIN) see raw values.
--    All other roles see masked/redacted output.
-- -----------------------------------------------------------------------------

-- Email: preserve first two characters and domain, mask the rest
CREATE OR REPLACE MASKING POLICY CUSTOMER_360.APP.EMAIL_MASK AS (val STRING) RETURNS STRING ->
  CASE
    WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'SYSADMIN') THEN val
    ELSE REGEXP_REPLACE(val, '(^[^@]{2})[^@]*(@.*)', '\\1***\\2')
  END;

-- Phone: preserve country code prefix and last two digits, mask middle digits
CREATE OR REPLACE MASKING POLICY CUSTOMER_360.APP.PHONE_MASK AS (val STRING) RETURNS STRING ->
  CASE
    WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'SYSADMIN') THEN val
    ELSE REGEXP_REPLACE(val, '(\\+?\\d{1,3}[-.]?)\\d{6,}(\\d{2})', '\\1******\\2')
  END;

-- Financial: return NULL for non-privileged roles (income, credit score, etc.)
CREATE OR REPLACE MASKING POLICY CUSTOMER_360.APP.FINANCIAL_MASK AS (val NUMBER) RETURNS NUMBER ->
  CASE
    WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'SYSADMIN') THEN val
    ELSE NULL
  END;

-- -----------------------------------------------------------------------------
-- 2. Apply Masking Policies to Dynamic Table
-- -----------------------------------------------------------------------------

ALTER TABLE CUSTOMER_360.CLEAN.DT_CUSTOMERS MODIFY COLUMN EMAIL SET MASKING POLICY CUSTOMER_360.APP.EMAIL_MASK;
ALTER TABLE CUSTOMER_360.CLEAN.DT_CUSTOMERS MODIFY COLUMN PHONE SET MASKING POLICY CUSTOMER_360.APP.PHONE_MASK;

-- Fallback: if dynamic tables do not support masking policies, apply to RAW instead
-- ALTER TABLE CUSTOMER_360.RAW.RAW_CUSTOMERS MODIFY COLUMN EMAIL SET MASKING POLICY CUSTOMER_360.APP.EMAIL_MASK;
-- ALTER TABLE CUSTOMER_360.RAW.RAW_CUSTOMERS MODIFY COLUMN PHONE SET MASKING POLICY CUSTOMER_360.APP.PHONE_MASK;

-- -----------------------------------------------------------------------------
-- 3. Object Tags
--    PII_LEVEL  - classifies columns by sensitivity (HIGH / MEDIUM / LOW)
--    DATA_DOMAIN - classifies tables by business domain
-- -----------------------------------------------------------------------------

CREATE TAG IF NOT EXISTS CUSTOMER_360.APP.PII_LEVEL ALLOWED_VALUES 'HIGH', 'MEDIUM', 'LOW';
CREATE TAG IF NOT EXISTS CUSTOMER_360.APP.DATA_DOMAIN ALLOWED_VALUES 'CUSTOMER', 'POLICY', 'CLAIM', 'LOAN', 'INTERACTION', 'DOCUMENT';

-- -----------------------------------------------------------------------------
-- 4. Apply Tags to RAW_CUSTOMERS
-- -----------------------------------------------------------------------------

-- Table-level domain tag
ALTER TABLE CUSTOMER_360.RAW.RAW_CUSTOMERS SET TAG CUSTOMER_360.APP.DATA_DOMAIN = 'CUSTOMER';

-- Column-level PII tags
ALTER TABLE CUSTOMER_360.RAW.RAW_CUSTOMERS MODIFY COLUMN EMAIL SET TAG CUSTOMER_360.APP.PII_LEVEL = 'HIGH';
ALTER TABLE CUSTOMER_360.RAW.RAW_CUSTOMERS MODIFY COLUMN PHONE SET TAG CUSTOMER_360.APP.PII_LEVEL = 'HIGH';
ALTER TABLE CUSTOMER_360.RAW.RAW_CUSTOMERS MODIFY COLUMN ANNUAL_INCOME SET TAG CUSTOMER_360.APP.PII_LEVEL = 'MEDIUM';
ALTER TABLE CUSTOMER_360.RAW.RAW_CUSTOMERS MODIFY COLUMN CREDIT_SCORE SET TAG CUSTOMER_360.APP.PII_LEVEL = 'MEDIUM';
