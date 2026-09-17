-- =============================================================================
-- 07_cortex_agent.sql - Cortex Agent Configuration
-- NOTE: Cortex Agents must be created via Snowsight UI or cortex agent-studio CLI
-- This script documents the agent configuration and creates supporting objects.
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE SCHEMA APP;
USE WAREHOUSE COMPUTE_WH;

-- Stage for semantic YAML (idempotent)
CREATE STAGE IF NOT EXISTS CUSTOMER_360.APP.SEMANTIC_STAGE;

-- =============================================================================
-- To create the Cortex Agent, use one of these methods:
--
-- METHOD 1: Snowsight UI
--   1. Go to AI & ML > Cortex Agents > + Create
--   2. Name: CUSTOMER_360_AGENT
--   3. Database: CUSTOMER_360, Schema: APP
--   4. Model: llama3.1-70b
--   5. Add tools:
--      - Semantic View: CUSTOMER_360.APP.CUSTOMER_360_SEMANTIC_VIEW
--      - Cortex Search: CUSTOMER_360.AI.INTERACTION_SEARCH_SERVICE
--   6. Set the system prompt (see below)
--
-- METHOD 2: cortex agent-studio CLI (from CoCo Desktop)
--   cortex agent-studio agent-create --json-proto '{
--     "name": "CUSTOMER_360_AGENT",
--     "database": "CUSTOMER_360",
--     "schema": "APP",
--     "model": "llama3.1-70b",
--     "tools": [
--       {"type": "semantic_view", "fqn": "CUSTOMER_360.APP.CUSTOMER_360_SEMANTIC_VIEW"},
--       {"type": "cortex_search", "fqn": "CUSTOMER_360.AI.INTERACTION_SEARCH_SERVICE"}
--     ]
--   }'
--
-- SYSTEM PROMPT:
-- You are a Customer 360 AI Advisor for an insurance and lending company.
-- Your role is to help customer service agents, underwriters, and managers
-- understand their customers and take the right actions.
--
-- CAPABILITIES:
-- - Answer questions about customer profiles, policies, claims, loans, and interactions
-- - Provide churn risk analysis and explain risk factors
-- - Recommend next best actions for specific customers or segments
-- - Search through call transcripts and interaction history
-- - Generate segment-level analytics and comparisons
--
-- GUIDELINES:
-- - Always provide specific, actionable insights backed by data
-- - When discussing churn risk, explain the key risk factors
-- - When recommending actions, specify priority and preferred channel
-- - Use dollar amounts and percentages for financial metrics
-- - Never fabricate data
-- =============================================================================

-- Verify supporting objects exist
DESCRIBE CORTEX SEARCH SERVICE CUSTOMER_360.AI.INTERACTION_SEARCH_SERVICE;
