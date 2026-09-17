-- =============================================================================
-- 00_setup.sql - Database, Schemas, and Warehouse Configuration
-- Customer 360 + AI-Powered Next Best Action Engine
-- =============================================================================

USE ROLE ACCOUNTADMIN;

-- Database (already exists, idempotent)
CREATE DATABASE IF NOT EXISTS CUSTOMER_360;

-- Medallion Architecture Schemas
CREATE SCHEMA IF NOT EXISTS CUSTOMER_360.RAW
  COMMENT = 'Landing zone for all source data';

CREATE SCHEMA IF NOT EXISTS CUSTOMER_360.CLEAN
  COMMENT = 'Deduped, typed, validated via dynamic tables';

CREATE SCHEMA IF NOT EXISTS CUSTOMER_360.CURATED
  COMMENT = 'Joined unified customer 360 and interaction timeline';

CREATE SCHEMA IF NOT EXISTS CUSTOMER_360.AI
  COMMENT = 'AI-enriched outputs: sentiment, churn risk, next best action';

CREATE SCHEMA IF NOT EXISTS CUSTOMER_360.APP
  COMMENT = 'Semantic views, Cortex Agent, Streamlit serving layer';

-- Warehouse (already exists, ensure config)
ALTER WAREHOUSE IF EXISTS COMPUTE_WH SET
  AUTO_SUSPEND = 300
  AUTO_RESUME = TRUE;

-- Context for subsequent scripts
USE DATABASE CUSTOMER_360;
USE WAREHOUSE COMPUTE_WH;
