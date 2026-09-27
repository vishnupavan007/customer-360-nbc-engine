# Customer 360 - Next Best Action Engine

AI-powered unified customer intelligence platform for insurance and lending, built on Snowflake Cortex AI. Built for the Snowflake CoCo Hackathon.

---

## Overview

Insurers and lenders struggle to act on fragmented customer data spread across policies, claims, loans, emails, and call transcripts. This solution unifies all structured and unstructured touchpoints into a single Customer 360 view and uses Snowflake Cortex AI to automatically score churn risk, analyse call sentiment, extract structured data from documents, and recommend the next best action for every customer — all accessible through a conversational Streamlit application.

**Key capabilities:**
- Unified 360-degree customer view joining policies, claims, loans, interactions, and call transcripts
- AI-powered churn risk scoring with explanation of risk factors
- Call sentiment analysis and summarisation on unstructured transcripts
- Next Best Action recommendations with channel and priority
- Document Intelligence: AI-powered structured field extraction from insurance claim forms and policy summaries
- Conversational AI advisor for natural-language analytics
- Cortex Search over interaction records for RAG-based retrieval
- Multilingual customer summaries via CORTEX.TRANSLATE
- What-If Simulator for interactive churn prediction
- Customer Health Score (composite A-F grade from 5 weighted factors)
- Proactive alerts: auto-email on churn spikes, AI quality degradation, VIP complaints
- Automated NBA-to-email retention workflow with AI-generated personalized emails
- Row access policies for role-based regional data isolation
- Data masking policies on PII columns (email, phone)
- Data Metric Functions monitoring AI parse failure rates
- Semantic view with 5 tables, 10 verified queries for Cortex Analyst
- 33-test SQL validation suite, resource monitor, and daily synthetic data pipeline
- 10-page Streamlit app with dark/light theme, CSV export, date filters
- Data Lineage page with pipeline architecture visualization
- Snowflake Notebook for exploratory customer analysis

---

## Architecture

```
RAW (7 tables — landing zone)
  └── CLEAN (6 dynamic tables, DOWNSTREAM lag)
        └── CURATED (2 dynamic tables, DOWNSTREAM)
              └── AI (6 dynamic tables — 60 min / 5 min lag + 1 Cortex Search Service)
                    └── APP (semantic view, Cortex Search, Streamlit)
```

### Data Flow

```
RAW_CUSTOMERS ──┐
RAW_POLICIES ───┤
RAW_CLAIMS ─────┤─► DT_CUSTOMERS/POLICIES/CLAIMS/LOANS/INTERACTIONS/TRANSCRIPTS
RAW_LOANS ──────┤        (CLEAN schema, deduplicated + normalised)
RAW_INTERACTIONS┤
RAW_CALL_TRANS ─┘         │
                           ▼
                  CUSTOMER_360_UNIFIED + CUSTOMER_INTERACTION_TIMELINE
                       (CURATED schema, 6-way aggregation join)
                           │
              ┌────────────┼────────────────┐
              ▼            ▼                ▼
   DT_TRANSCRIPT_SENTIMENT  DT_CHURN_RISK   DT_NEXT_BEST_ACTION
   (CORTEX.SENTIMENT +      (CORTEX.COMPLETE (CORTEX.COMPLETE
    CORTEX.SUMMARIZE)        llama3.1-8b)     llama3.1-8b)
              │
              ▼
   INTERACTION_SEARCH_SERVICE (Cortex Search, 1-hour lag)
              │
              ▼
   CUSTOMER_360_SEMANTIC_VIEW + CUSTOMER_360_APP (Streamlit)

RAW_DOCUMENTS ──► DT_DOCUMENT_PARSED ──► DT_DOCUMENT_EXTRACTED
                                          (CORTEX.COMPLETE llama3.1-8b
                                           structured field extraction)
```

---

## Snowflake Objects

| Schema | Object | Type | Purpose |
|--------|--------|------|---------|
| RAW | RAW_CUSTOMERS, RAW_POLICIES, RAW_CLAIMS, RAW_LOANS, RAW_INTERACTIONS, RAW_CALL_TRANSCRIPTS | Tables | Source landing zone |
| RAW | RAW_DOCUMENTS | Table | Insurance document content (claim forms, policy summaries) |
| CLEAN | DT_CUSTOMERS, DT_POLICIES, DT_CLAIMS, DT_LOANS, DT_INTERACTIONS, DT_CALL_TRANSCRIPTS | Dynamic Tables (DOWNSTREAM) | Dedup, normalise, derive columns |
| CURATED | CUSTOMER_360_UNIFIED | Dynamic Table (DOWNSTREAM) | Master 360 record per customer |
| CURATED | CUSTOMER_INTERACTION_TIMELINE | Dynamic Table (DOWNSTREAM) | Chronological event stream, all touchpoints |
| AI | DT_TRANSCRIPT_SENTIMENT | Dynamic Table (60 min lag) | Sentiment score + call summary via CORTEX.SENTIMENT + CORTEX.SUMMARIZE |
| AI | DT_CHURN_RISK | Dynamic Table (60 min lag) | Churn risk score + risk factors via CORTEX.COMPLETE (llama3.1-8b) |
| AI | DT_NEXT_BEST_ACTION | Dynamic Table (60 min lag) | NBA recommendation + channel + rationale via CORTEX.COMPLETE (llama3.1-8b) |
| AI | DT_DOCUMENT_PARSED | Dynamic Table (5 min lag) | Cleaned document content from RAW layer |
| AI | DT_DOCUMENT_EXTRACTED | Dynamic Table (5 min lag) | AI-extracted structured fields from documents via CORTEX.COMPLETE (llama3.1-8b) |
|| AI | DT_CUSTOMER_HEALTH_SCORE | Dynamic Table (60 min lag) | Composite health score (A-F grade) from 5 weighted factors |
| AI | INTERACTION_SEARCH_SERVICE | Cortex Search Service (1 hr lag) | RAG over call transcripts + interaction notes |
| APP | Customer360SemanticView | Semantic View | 5 tables, 19 measures, 10 verified queries for Cortex Analyst |
| APP | CUSTOMER_360_AGENT | Cortex Agent | Document-aware AI advisor (llama3.1-70b) |
| APP | CUSTOMER_360_APP | Streamlit App | 10-page dashboard + AI chat + What-If simulator |
| APP | RUN_APP_TESTS | Stored Procedure | 33-test SQL validation suite |
| APP | SP_SEND_NBA_EMAILS | Stored Procedure | Automated NBA retention email workflow |
| APP | CUSTOMER_SUMMARY_TRANSLATED | Function | Multilingual summaries via CORTEX.TRANSLATE |
| APP | EMAIL_MASK, PHONE_MASK, FINANCIAL_MASK | Masking Policies | PII protection |
| APP | REGION_ACCESS_POLICY | Row Access Policy | Role-based regional data isolation |
| APP | CHURN/NBA_PARSE_FAILURE_RATE | Data Metric Functions | AI quality monitoring |
| APP | AI_QUALITY_DASHBOARD | View | AI model quality metrics |
| APP | ALERT_HIGH_CHURN_RISK | Alert (60 min) | Email on critical churn risk |
| APP | ALERT_AI_QUALITY_DEGRADATION | Alert (6 hr) | Email on AI parse failure > 5% |
| APP | ALERT_VIP_COMPLAINT | Alert (30 min) | Email on VIP/Premium complaints |
| APP | CHECK_CHURN_COMPLETENESS, CHECK_NBA_COMPLETENESS, CHECK_CHURN_RANGE, CHECK_SENTIMENT_RANGE | Tasks (daily 8 AM ET) | AI output quality monitoring |
| APP | PIPELINE_HEALTH_CHECK | Task (every 6 hours) | Pipeline health logging |
| APP | AI_QUALITY_LOG | Table | Quality check results |
| APP | NBA_EMAIL_LOG | Table | AI-generated retention email audit log |
| APP | ROLE_REGION_MAPPING | Table | Role-to-country access mapping |
| RAW | SP_DAILY_SYNTHETIC_DATA | Stored Procedure | Generates daily synthetic data across all 6 RAW tables |
| RAW | TASK_DAILY_RAW_INGEST | Task (daily midnight UTC) | Calls SP_DAILY_SYNTHETIC_DATA(20) |

---

## Synthetic Data

The project generates realistic, referentially consistent synthetic data — no production data required:

| Table | Initial Rows | Description |
|-------|-------------|-------------|
| RAW_CUSTOMERS | 500+ | Multi-country customers (USA, UK, Canada, India, Singapore, Australia) across 4 segments |
| RAW_POLICIES | 800+ | Auto, Home, Life, Health, Travel policies with underwriting scores |
| RAW_CLAIMS | 300+ | Claims with status, amounts, and settlement ratios |
| RAW_LOANS | 400+ | Mortgage, Auto, Personal, Business loans with delinquency data |
| RAW_INTERACTIONS | 1,200+ | Structured touchpoints across Email, Phone, Chat, Branch, Web, Mobile |
| RAW_CALL_TRANSCRIPTS | 250+ | Realistic multi-turn call transcripts (10 unique scenarios) |
| RAW_DOCUMENTS | 20 | Insurance claim forms (10) and policy summaries (10) with realistic multi-paragraph text |

A daily ingest task (`TASK_DAILY_RAW_INGEST`) adds ~20 new customers and proportional data across all tables each day. Row counts grow over time.

---

## AI Enrichment Details

### Sentiment Analysis (`DT_TRANSCRIPT_SENTIMENT`)
- Uses `SNOWFLAKE.CORTEX.SENTIMENT()` to score each call transcript (-1 to 1)
- Uses `SNOWFLAKE.CORTEX.SUMMARIZE()` to generate a 2-3 sentence call summary
- Optimised with CTE to call SENTIMENT once per row (avoids double billing)
- Labels: Positive (>= 0.3), Negative (<= -0.3), Neutral

### Churn Risk Scoring (`DT_CHURN_RISK`)
- Uses `SNOWFLAKE.CORTEX.COMPLETE(llama3.1-8b)` with a structured prompt
- Input: 16 customer features (segment, tenure, policies, claims, complaints, sentiment, loans)
- Output: JSON with `churn_risk_score` (0-1), `risk_factors` (array), `retention_urgency`, `confidence`
- Uses `REGEXP_SUBSTR` + `TRY_PARSE_JSON` to extract JSON from LLM output reliably

### Next Best Action (`DT_NEXT_BEST_ACTION`)
- Uses `SNOWFLAKE.CORTEX.COMPLETE(llama3.1-8b)` combining churn risk + sentiment + profile
- Output: JSON with `action_type`, `action_description`, `priority`, `channel`, `rationale`
- Action types: Retention_Offer, Policy_Review, Claims_Followup, Upsell, Payment_Assistance, Proactive_Outreach, Renewal_Reminder, Complaint_Resolution

### Cortex Search Service
- Indexes all call transcripts + interaction notes
- Enables semantic search across unstructured interaction history
- Refreshes incrementally every hour

### Document Intelligence (`DT_DOCUMENT_PARSED` + `DT_DOCUMENT_EXTRACTED`)
- `DT_DOCUMENT_PARSED`: sources from `RAW.RAW_DOCUMENTS`, filters empty text, deduplicates — same pattern as `DT_CALL_TRANSCRIPTS` sourcing from `RAW_CALL_TRANSCRIPTS`
- `DT_DOCUMENT_EXTRACTED`: uses `SNOWFLAKE.CORTEX.COMPLETE(llama3.1-8b)` to extract structured fields from document text — same JSON extraction pattern as churn risk scoring
- Extracted fields: reference number, policy number, customer name, customer ID, document date, amount, category, status, description
- Cross-references extracted customer IDs against the Customer 360 unified profile
- Both dynamic tables refresh on a 5-minute target lag

---

## Semantic View

`CUSTOMER_360.APP.Customer360SemanticView` covers 5 fact tables with 10 verified queries:

| Verified Query | Question |
|---------------|---------|
| high_risk_premium_customers | How many high-risk churn customers are in the Premium segment? |
| avg_sentiment_by_segment | What is the average sentiment score by customer segment? |
| top_churn_risk_with_nba | Show top 10 customers by churn risk with their next best action |
| common_nba_negative_sentiment | What are the most common next best actions for customers with negative sentiment? |
| customer_count_by_segment_country | How many customers are there by segment and country? |
| churn_risk_distribution | What is the distribution of churn risk scores? |
| open_claims_high_churn | Which customers have open claims and high churn risk? |
| avg_premium_by_country | What is the average total premium by country? |
| delinquent_loans_by_segment | How many customers have loans more than 90 days past due by segment? |

---

## Streamlit Application

**Live URL:** `https://app.snowflake.com/ap-southeast-7.aws/sq84485/#/streamlit-apps/CUSTOMER_360.APP.CUSTOMER_360_APP`

| Page | Description |
|------|-------------|
| Home (`app.py`) | KPI dashboard (5 metrics), customer onboarding trend, sentiment + churn charts, top action queue |
| Customer 360 (`1_Customer_360.py`) | Search by name/ID; unified profile with 5 tabs (Profile, Policies/Claims, Loans, Interactions, Documents) + AI insights |
| Churn Risk (`2_Churn_Risk.py`) | Filterable dashboard with risk distribution, segment breakdown, detail table + CSV download |
| Sentiment (`3_Sentiment.py`) | Sentiment by agent/reason, weekly trend chart, date range filter, negative call drill-down |
| Next Best Action (`4_Next_Best_Action.py`) | Filterable NBA queue with priority/type filters, charts, CSV download |
| AI Advisor (`5_AI_Advisor.py`) | Conversational chat with 3-tier routing (guard → SQL fast-path → Cortex AI), styled bubbles |
| Operations (`6_Operations.py`) | Pipeline health: layer counts, DT status, task history, refresh history |
| Documents (`7_Documents.py`) | Document Intelligence: KPIs, extracted fields + CSV download, viewer, customer cross-reference |
| What-If Simulator (`8_What_If.py`) | Interactive churn prediction — adjust parameters and see AI-predicted risk change |
| Data Lineage (`9_Data_Lineage.py`) | Pipeline architecture diagram, layer counts, governance status, AI quality, active alerts |

---

## Project Structure

```
customer-360-nbc-engine/
│
├── infrastructure/
│   └── 00_setup.sql              # One-time: database, schemas, warehouse
│
├── pipeline/                     # Data pipeline (run independently per layer)
│   ├── schema/
│   │   └── 01_raw_tables.sql     # RAW landing table DDL (7 tables)
│   ├── data/
│   │   ├── 02_synthetic_data.sql # Synthetic data generation (3,450+ rows)
│   │   ├── 02b_additional_10k_data.sql  # Additional data batch
│   │   ├── 02c_transcripts_fix.sql      # Transcript data fixes
│   │   └── 02d_synthetic_documents.sql  # 20 synthetic insurance documents
│   ├── clean/
│   │   └── 03_clean_dynamic_tables.sql   # CLEAN layer: 6 dynamic tables
│   ├── curated/
│   │   └── 04_curated_dynamic_tables.sql # CURATED layer: unified 360 + timeline
│   ├── ai/
│   │   └── 05_ai_enrichment.sql  # AI layer: sentiment, churn, NBA, Cortex Search
│   └── documents/
│       └── 12_document_processing.sql  # Document AI: CORTEX.COMPLETE extraction
│
├── serving/                      # Analytical serving layer
│   ├── semantic_model/
│   │   ├── 06_semantic_model.sql
│   │   └── customer_360_semantic.yaml  # 4 tables, 9 verified queries
│   └── agent/
│       └── 07_cortex_agent.sql   # Cortex Agent configuration (Snowsight UI)
│
├── ops/                          # Operations: monitoring and validation
│   ├── 08_tasks_and_monitoring.sql  # 5 scheduled quality monitoring tasks
│   ├── 09_validation.sql         # End-to-end validation queries
│   ├── 10_daily_raw_pipeline.sql # Daily synthetic data SP + task
│   └── 11_app_test_suite.sql     # SQL test suite (23 tests, CALL APP.RUN_APP_TESTS())
│
├── app/                          # Streamlit application (self-contained)
│   ├── app.py                    # Home dashboard
│   ├── utils.py                  # Shared utilities
│   ├── snowflake.yml             # SiS deployment manifest
│   ├── pyproject.toml            # Python package config
│   ├── environment.yml           # SiS environment
│   └── pages/
│       ├── 1_Customer_360.py     # Customer search + unified view
│       ├── 2_Churn_Risk.py       # Churn risk dashboard
│       ├── 3_Sentiment.py        # Call sentiment analysis
│       ├── 4_Next_Best_Action.py # NBA recommendations
│       ├── 5_AI_Advisor.py       # AI chat interface
│       ├── 6_Operations.py       # Pipeline monitoring dashboard
│       └── 7_Documents.py        # Document Intelligence viewer
│
├── scripts/                      # Deployment + orchestration
│   ├── run_pipeline.py           # Execute all SQL layers via connector
│   ├── deploy_semantic.py        # Deploy semantic view via Snowpark
│   └── deploy_streamlit.py       # Deploy Streamlit app via snow CLI
│
├── .env                          # Credentials (gitignored)
└── README.md
```

---

## Deployment

### Prerequisites

```powershell
pip install snowflake-connector-python python-dotenv snowflake-snowpark-python snowflake-cli
```

### 1. Configure `.env`

```env
SNOWFLAKE_ACCOUNT=your-account-identifier
SNOWFLAKE_USER=your-username
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_ROLE=ACCOUNTADMIN
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
```

### 2. Grant required privileges (run in Snowsight once)

```sql
USE ROLE ACCOUNTADMIN;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE ACCOUNTADMIN;
GRANT USE AI FUNCTIONS ON ACCOUNT TO ROLE ACCOUNTADMIN;
```

### 3. Run the SQL pipeline

```powershell
python scripts/run_pipeline.py
```

Executes all layers in order (infrastructure → pipeline → serving → ops). Scripts 03-05 create dynamic tables that begin refreshing automatically.

### 4. Deploy document processing and synthetic documents

```sql
-- Run in Snowsight or via connector:
-- pipeline/data/02d_synthetic_documents.sql
-- pipeline/documents/12_document_processing.sql
```

### 5. Deploy the semantic view

```powershell
python scripts/deploy_semantic.py
```

Or create it manually in Snowsight: AI & ML > Cortex Analyst > paste the YAML from `serving/semantic_model/customer_360_semantic.yaml`.

### 6. Deploy the Streamlit app

```powershell
python scripts/deploy_streamlit.py
```

### 7. Create the Cortex Agent (Snowsight UI)

See `serving/agent/07_cortex_agent.sql` for instructions. Create via AI & ML > Cortex Agents with:
- Semantic View: `CUSTOMER_360.APP.Customer360SemanticView`
- Cortex Search: `CUSTOMER_360.AI.INTERACTION_SEARCH_SERVICE`

---

## Security Notes

- SQL injection prevention: allowlist-based input sanitization, single-quote removal from character filters
- XSS prevention: `html.escape()` on all values rendered via `unsafe_allow_html`
- Data masking: EMAIL_MASK, PHONE_MASK, FINANCIAL_MASK policies on PII columns
- Row access policy: REGION_ACCESS_POLICY isolates data by role→country mapping
- PII tagging: PII_LEVEL (HIGH/MEDIUM/LOW) and DATA_DOMAIN tags on sensitive columns
- Passwords passed via environment variable, not CLI arguments
- `.env` is gitignored
- AI Advisor shows disclaimer when falling back to LLM (non-live data)
- Resource monitor: 100 credit/month with 75%/90%/100% triggers (notify/suspend)

---

## Cost Profile

Approximate credit consumption on AWS AP-Southeast-7 (Enterprise):

| Service | Rate | Usage |
|---------|------|-------|
| AI Functions (COMPLETE, SENTIMENT, SUMMARIZE) | ~$2/credit | Very low — runs once per row on DT refresh |
| Warehouse compute | $3.60/credit | Auto-suspends after 5 min idle |
| Cortex Search | ~$2/credit | Incremental refresh every hour |
| Streamlit container | $3.60/credit | Scales to zero when not in use |

Dynamic tables with `TARGET_LAG = DOWNSTREAM` only refresh when queried, not on a fixed schedule — minimising idle compute costs.

---

## Built With

- Snowflake Dynamic Tables (14 total — incremental ETL pipeline)
- Snowflake Cortex AI: `CORTEX.SENTIMENT`, `CORTEX.SUMMARIZE`, `CORTEX.COMPLETE`, `CORTEX.TRANSLATE`
- Cortex Search Service (semantic search over unstructured interactions)
- Cortex Agent (llama3.1-70b orchestration with semantic view + search tools)
- Semantic Views + Cortex Analyst (natural language to SQL, 10 verified queries)
- Streamlit-in-Snowflake (10-page dashboard with dark/light theme)
- Snowflake Alerts (3 proactive email notifications)
- Data Masking Policies + Row Access Policies (PII protection + regional isolation)
- Data Metric Functions (automated AI quality monitoring)
- Resource Monitor (100 credit/month with suspend trigger)
- Snowflake Notebook (exploratory analysis companion)
- 3 CoCo Skills (customer snapshot, NBA campaign report, pipeline health)
- Snowflake CoCo Desktop (planning, development, execution, testing)
- GitHub Actions CI/CD for automated Streamlit deployment
- Slack MCP integration for cross-surface collaboration


