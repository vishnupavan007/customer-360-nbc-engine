-- =============================================================================
-- 17_row_access_policy.sql - Role-Based Data Isolation
-- Restricts customer data visibility by geographic region per role
-- Enterprise-grade multi-tenant security for branch/regional teams
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE SCHEMA APP;
USE WAREHOUSE COMPUTE_WH;

-- =========================================================================
-- Role-to-region mapping table
-- Maps Snowflake roles to the countries they can access
-- 'ALL' grants access to every country (admin roles)
-- =========================================================================
CREATE OR REPLACE TABLE ROLE_REGION_MAPPING (
    ROLE_NAME VARCHAR NOT NULL,
    ALLOWED_COUNTRY VARCHAR NOT NULL
);

INSERT INTO ROLE_REGION_MAPPING VALUES
  ('ACCOUNTADMIN', 'ALL'),
  ('SYSADMIN', 'ALL'),
  ('US_TEAM', 'USA'),
  ('UK_TEAM', 'UK'),
  ('APAC_TEAM', 'JAPAN'),
  ('APAC_TEAM', 'AUSTRALIA'),
  ('APAC_TEAM', 'SINGAPORE'),
  ('APAC_TEAM', 'INDIA');

-- =========================================================================
-- Row Access Policy
-- Applied to CUSTOMER_360_UNIFIED.COUNTRY column
-- Admin roles see everything; regional roles see only their countries
-- =========================================================================
CREATE OR REPLACE ROW ACCESS POLICY REGION_ACCESS_POLICY
  AS (country VARCHAR) RETURNS BOOLEAN ->
    CURRENT_ROLE() IN ('ACCOUNTADMIN', 'SYSADMIN')
    OR EXISTS (
      SELECT 1 FROM CUSTOMER_360.APP.ROLE_REGION_MAPPING
      WHERE ROLE_NAME = CURRENT_ROLE()
        AND (ALLOWED_COUNTRY = 'ALL' OR ALLOWED_COUNTRY = country)
    );

-- Apply to the unified customer table
ALTER TABLE CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED
  ADD ROW ACCESS POLICY REGION_ACCESS_POLICY ON (COUNTRY);

-- =========================================================================
-- Verification: ACCOUNTADMIN should see all countries
-- A US_TEAM role would only see USA rows
-- =========================================================================
-- SELECT COUNTRY, COUNT(*) FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED GROUP BY COUNTRY;
