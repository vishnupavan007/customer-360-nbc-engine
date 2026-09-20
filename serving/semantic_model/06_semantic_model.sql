-- =============================================================================
-- 06_semantic_model.sql - Semantic View Creation
-- Uploads YAML to stage and creates semantic view
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE SCHEMA APP;
USE WAREHOUSE COMPUTE_WH;

-- Create stage for semantic YAML
CREATE STAGE IF NOT EXISTS CUSTOMER_360.APP.SEMANTIC_STAGE;

-- NOTE: The old syntax "CREATE SEMANTIC VIEW ... FROM @stage/file.yaml" does not work.
-- Use the stored procedure SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML instead.
-- The YAML must be passed as a string (not a stage reference).
-- The procedure reads the 'name' field from the YAML to name the view.
-- Also, the YAML must use native semantic view format (facts/metrics, relationship_columns)
-- not legacy Cortex Analyst format (measures, join_type, on).

-- Option A: Upload YAML to stage, then read it into the procedure
-- snow stage copy customer_360_semantic.yaml @CUSTOMER_360.APP.SEMANTIC_STAGE
-- Then run:
-- CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML('CUSTOMER_360.APP',
--   (SELECT $1 FROM @CUSTOMER_360.APP.SEMANTIC_STAGE/customer_360_semantic.yaml));

-- Option B: Pass YAML inline (reliable, no stage dependency):
CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  'CUSTOMER_360.APP',
  -- Paste the full YAML contents between $$ delimiters
  -- See customer_360_semantic.yaml for the source
  (SELECT TO_VARCHAR(SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b', 'respond with only: use inline YAML')))
  -- Replace the above placeholder with the actual YAML content wrapped in $$...$$ delimiters
);

-- Verify the semantic view
SHOW SEMANTIC VIEWS IN SCHEMA CUSTOMER_360.APP;
