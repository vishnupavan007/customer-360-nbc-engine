-- =============================================================================
-- 07_cortex_agent.sql - Cortex Agent Creation
-- Run this script in Snowsight (not via connector - DDL requires Snowsight).
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE SCHEMA APP;
USE WAREHOUSE COMPUTE_WH;

-- =============================================================================
-- FIXES APPLIED (vs. original broken version):
--
--   1. CREATE OR REPLACE CORTEX AGENT  →  CREATE OR REPLACE AGENT
--      "CORTEX AGENT" is not a valid DDL object keyword; correct syntax is AGENT.
--
--   2. Inline SQL-style properties (SYSTEM_PROMPT='...', MODEL='...', TOOLS=(...))
--      →  FROM SPECIFICATION $$ <yaml> $$
--      Agent configuration must be expressed as a YAML spec block.
--
--   3. GRANT USAGE ON CORTEX AGENT  →  GRANT USAGE ON AGENT
--      Grant object type must match the DDL object type.
--
--   4. semantic_view reference CUSTOMER_360.APP.CUSTOMER_360_SEMANTIC_VIEW
--      →  CUSTOMER_360.APP.CUSTOMER360SEMANTICVIEW
--      The actual object name has no underscores between CUSTOMER360 and SEMANTIC.
--      This was the root cause of silent CREATE AGENT failure (bad reference).
-- =============================================================================

CREATE OR REPLACE AGENT CUSTOMER_360.APP.CUSTOMER_360_AGENT
  COMMENT = 'Customer 360 AI advisor for insurance and lending - answers questions about customers, churn risk, sentiment, and recommends next best actions'
  FROM SPECIFICATION $$
models:
  orchestration: "llama3.1-70b"

instructions:
  system: |
    You are a Customer 360 AI Advisor for SecureLife, an insurance and lending company.
    Your role is to help customer service agents, underwriters, and managers
    understand their customers and take the right actions.

    CAPABILITIES:
    - Answer questions about customer profiles, policies, claims, loans, and interactions
    - Provide churn risk analysis and explain risk factors
    - Recommend next best actions for specific customers or segments
    - Search through call transcripts and interaction history
    - Generate segment-level analytics and comparisons

    DATA MODEL:
    - Customers have segments: Basic, Standard, Premium, VIP
    - Churn risk score: 0.0 (low) to 1.0 (critical)
    - Retention urgency: Low / Medium / High / Critical
    - Next best actions have types: Retention Call, Policy Review, Loan Refinance,
      Premium Discount, Claims Expedite, Loyalty Reward, Service Recovery
    - Sentiment: Positive (score >= 0.3), Neutral, Negative (score <= -0.3)

    GUIDELINES:
    - Always provide specific, actionable insights backed by data
    - When discussing churn risk, explain the key risk factors
    - When recommending actions, specify priority and preferred channel
    - Use dollar amounts and percentages for financial metrics
    - Never fabricate data — only report what the data shows

tools:
  - tool_spec:
      type: "cortex_analyst_text_to_sql"
      name: "SemanticView1"
  - tool_spec:
      type: "cortex_search"
      name: "SearchService1"

tool_resources:
  SemanticView1:
    semantic_view: "CUSTOMER_360.APP.CUSTOMER360SEMANTICVIEW"
  SearchService1:
    cortex_search_service: "CUSTOMER_360.AI.INTERACTION_SEARCH_SERVICE"
$$;

-- Grant access to PUBLIC role so all users can invoke the agent
GRANT USAGE ON AGENT CUSTOMER_360.APP.CUSTOMER_360_AGENT TO ROLE PUBLIC;

-- Verify creation
SHOW AGENTS IN SCHEMA CUSTOMER_360.APP;
