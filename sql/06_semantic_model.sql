-- =============================================================================
-- 06_semantic_model.sql - Semantic View Creation
-- Uploads YAML to stage and creates semantic view
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE SCHEMA APP;
USE WAREHOUSE COMPUTE_WH;

-- Create stage for semantic YAML
CREATE STAGE IF NOT EXISTS CUSTOMER_360.APP.SEMANTIC_STAGE;

-- NOTE: Upload the YAML file to the stage before running the next command.
-- In Snowsight: Data > CUSTOMER_360 > APP > Stages > SEMANTIC_STAGE > + Files
-- Or via CLI: snow stage copy semantic/customer_360_semantic.yaml @CUSTOMER_360.APP.SEMANTIC_STAGE
-- Or via Python: PUT file://semantic/customer_360_semantic.yaml @CUSTOMER_360.APP.SEMANTIC_STAGE

-- Create the semantic view from staged YAML
CREATE OR REPLACE SEMANTIC VIEW CUSTOMER_360.APP.CUSTOMER_360_SEMANTIC_VIEW
  FROM @CUSTOMER_360.APP.SEMANTIC_STAGE/customer_360_semantic.yaml;

-- Verify the semantic view
DESCRIBE SEMANTIC VIEW CUSTOMER_360.APP.CUSTOMER_360_SEMANTIC_VIEW;
