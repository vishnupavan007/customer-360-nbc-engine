# Customer 360 - Next Best Action Engine

AI-powered unified customer intelligence platform for insurance and lending, built on Snowflake Cortex AI. Built for the Snowflake CoCo Hackathon.

---

## Overview

Insurers and lenders struggle to act on fragmented customer data spread across policies, claims, loans, emails, and call transcripts. This solution unifies all structured and unstructured touchpoints into a single Customer 360 view and uses Snowflake Cortex AI to automatically score churn risk, analyse call sentiment, and recommend the next best action for every customer — all accessible through a conversational Streamlit application.

**Key capabilities:**
- Unified 360-degree customer view joining policies, claims, loans, interactions, and call transcripts
- AI-powered churn risk scoring with explanation of risk factors
- Call sentiment analysis and summarisation on unstructured transcripts
- Next Best Action recommendations with channel and priority
- Conversational AI advisor for natural-language analytics
- Cortex Search over 1,450+ interaction records for RAG-based retrieval
- Semantic view with 9 verified queries for Cortex Analyst

---

## Architecture

```
RAW (landing)
  └── CLEAN (dynamic tables, 1 min lag)
        └── CURATED (unified 360 view, downstream)
              └── AI (sentiment, churn, NBA, downstream)
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
                       (CURATED schema, 5-way aggregation join)
                           │
              ┌────────────┼────────────────┐
              ▼            ▼                ▼
   DT_TRANSCRIPT_SENTIMENT  DT_CHURN_RISK   DT_NEXT_BEST_ACTION
   (AI_SENTIMENT +          (AI_COMPLETE    (AI_COMPLETE
    AI_SUMMARIZE)            llama3.1-8b)    llama3.1-8b)
              │
              ▼
   INTERACTION_SEARCH_SERVICE (Cortex Search, 1-hour lag)
              │
              ▼
   CUSTOMER_360_SEMANTIC_VIEW + CUSTOMER_360_APP (Streamlit)
```

---

## Snowflake Objects

| Schema | Object | Type | Purpose |
|--------|--------|------|---------|
| RAW | RAW_CUSTOMERS, RAW_POLICIES, RAW_CLAIMS, RAW_LOANS, RAW_INTERACTIONS, RAW_CALL_TRANSCRIPTS | Tables | Source landing zone |
| CLEAN | DT_CUSTOMERS, DT_POLICIES, DT_CLAIMS, DT_LOANS, DT_INTERACTIONS, DT_CALL_TRANSCRIPTS | Dynamic Tables (1 min lag) | Dedup, normalise, derive columns |
| CURATED | CUSTOMER_360_UNIFIED | Dynamic Table (downstream) | 500-row master 360 record per customer |
| CURATED | CUSTOMER_INTERACTION_TIMELINE | Dynamic Table (downstream) | Chronological event stream, all touchpoints |
| AI | DT_TRANSCRIPT_SENTIMENT | Dynamic Table (5 min lag) | Sentiment score + call summary via AI_SENTIMENT + AI_SUMMARIZE |
| AI | DT_CHURN_RISK | Dynamic Table (downstream) | Churn risk score + risk factors via AI_COMPLETE (llama3.1-8b) |
| AI | DT_NEXT_BEST_ACTION | Dynamic Table (downstream) | NBA recommendation + channel + rationale via AI_COMPLETE (llama3.1-8b) |
| AI | INTERACTION_SEARCH_SERVICE | Cortex Search Service (1 hr lag) | RAG over 1,450 call transcripts + interaction notes |
| APP | CUSTOMER_360_SEMANTIC_VIEW | Semantic View | 4 tables, 19 measures, 9 verified queries for Cortex Analyst |
| APP | CUSTOMER_360_APP | Streamlit App | 5-page dashboard + AI chat advisor |
| APP | CHECK_CHURN_COMPLETENESS, CHECK_NBA_COMPLETENESS, CHECK_CHURN_RANGE, CHECK_SENTIMENT_RANGE | Tasks (daily 8 AM ET) | AI output quality monitoring |
| APP | PIPELINE_HEALTH_CHECK | Task (every 6 hours) | Pipeline health logging |
| APP | AI_QUALITY_LOG | Table | Quality check results |

---

## Synthetic Data

The project generates realistic, referentially consistent synthetic data — no production data required:

| Table | Rows | Description |
|-------|------|-------------|
| RAW_CUSTOMERS | 500 | Multi-country customers (USA, UK, Canada, India, Singapore, Australia) across 4 segments |
| RAW_POLICIES | 800 | Auto, Home, Life, Health, Travel policies with underwriting scores |
| RAW_CLAIMS | 300 | Claims with status, amounts, and settlement ratios |
| RAW_LOANS | 400 | Mortgage, Auto, Personal, Business loans with delinquency data |
| RAW_INTERACTIONS | 1,200 | Structured touchpoints across Email, Phone, Chat, Branch, Web, Mobile |
| RAW_CALL_TRANSCRIPTS | 250 | Realistic multi-turn call transcripts (10 unique scenarios) |

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
- Uses `REGEXP_SUBSTR` to extract JSON from LLM output reliably

### Next Best Action (`DT_NEXT_BEST_ACTION`)
- Uses `SNOWFLAKE.CORTEX.COMPLETE(llama3.1-8b)` combining churn risk + sentiment + profile
- Output: JSON with `action_type`, `action_description`, `priority`, `channel`, `rationale`
- Action types: Retention_Offer, Policy_Review, Claims_Followup, Upsell, Payment_Assistance, Proactive_Outreach, Renewal_Reminder, Complaint_Resolution

### Cortex Search Service
- Indexes 1,450 records: all 250 call transcripts + 1,200 interaction notes
- Enables semantic search across unstructured interaction history
- Refreshes incrementally every hour

---

## Semantic View

`CUSTOMER_360.APP.CUSTOMER_360_SEMANTIC_VIEW` covers 4 fact tables with 9 verified queries:

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
| Home (`app.py`) | KPI dashboard: total customers, active, high churn risk, high-priority actions; sentiment distribution and churn-by-segment charts; top action queue |
| Customer 360 (`1_Customer_360.py`) | Search by name or ID; unified profile with 4 tabs (Profile, Policies/Claims, Loans, Interactions) + AI insights panel |
| Churn Risk (`2_Churn_Risk.py`) | Filterable churn risk dashboard with risk distribution histogram, segment breakdown, and customer detail table |
| Sentiment (`3_Sentiment.py`) | Sentiment by agent, call reason, and label; negative call drill-down with full transcript viewer |
| Next Best Action (`4_Next_Best_Action.py`) | Filterable NBA queue by priority and action type; actions-by-type and actions-by-channel charts |
| AI Advisor (`5_AI_Advisor.py`) | Conversational chat interface; keyword-routed SQL queries for 7 canned questions; Cortex AI fallback with hallucination disclaimer |

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
│   │   └── 01_raw_tables.sql     # RAW landing table DDL
│   ├── data/
│   │   └── 02_synthetic_data.sql # Synthetic data generation (3,450+ rows)
│   ├── clean/
│   │   └── 03_clean_dynamic_tables.sql   # CLEAN layer: 6 dynamic tables
│   ├── curated/
│   │   └── 04_curated_dynamic_tables.sql # CURATED layer: unified 360 + timeline
│   └── ai/
│       └── 05_ai_enrichment.sql  # AI layer: sentiment, churn, NBA, Cortex Search
│
├── serving/                      # Analytical serving layer (evolves independently)
│   ├── semantic_model/
│   │   ├── 06_semantic_model.sql
│   │   └── customer_360_semantic.yaml  # 4 tables, 9 verified queries
│   └── agent/
│       └── 07_cortex_agent.sql   # Cortex Agent configuration (Snowsight UI)
│
├── ops/                          # Operations: monitoring and validation
│   ├── 08_tasks_and_monitoring.sql  # Scheduled quality monitoring tasks
│   └── 09_validation.sql         # End-to-end validation queries
│
├── app/                          # Streamlit application (self-contained)
│   ├── app.py                    # Home dashboard
│   ├── snowflake.yml             # SiS deployment manifest
│   ├── pyproject.toml            # Python package config (streamlit 1.52.2)
│   ├── environment.yml           # SiS environment (no external packages)
│   └── pages/
│       ├── 1_Customer_360.py     # Customer search + unified view
│       ├── 2_Churn_Risk.py       # Churn risk dashboard
│       ├── 3_Sentiment.py        # Call sentiment analysis
│       ├── 4_Next_Best_Action.py # NBA recommendations
│       └── 5_AI_Advisor.py       # AI chat interface
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

### 4. Deploy the semantic view

```powershell
python scripts/deploy_semantic.py
```

Or create it manually in Snowsight: AI & ML > Cortex Analyst > paste the YAML from `serving/semantic_model/customer_360_semantic.yaml`.

### 5. Deploy the Streamlit app

```powershell
python scripts/deploy_streamlit.py
```

### 6. Create the Cortex Agent (Snowsight UI)

See `sql/07_cortex_agent.sql` for instructions. Create via AI & ML > Cortex Agents with:
- Semantic View: `CUSTOMER_360.APP.CUSTOMER_360_SEMANTIC_VIEW`
- Cortex Search: `CUSTOMER_360.AI.INTERACTION_SEARCH_SERVICE`

---

## Security Notes

- All Streamlit pages use allowlist-based SQL filtering (no raw user input injected into SQL)
- Passwords are passed via environment variable, not CLI arguments
- `.env` is gitignored
- AI Advisor shows disclaimer when falling back to LLM (non-live data)

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

- Snowflake Dynamic Tables (incremental ETL pipeline)
- Snowflake Cortex AI: `AI_SENTIMENT`, `AI_SUMMARIZE`, `AI_COMPLETE` (llama3.1-8b)
- Cortex Search Service (semantic search over unstructured interactions)
- Semantic Views + Cortex Analyst (natural language to SQL)
- Streamlit-in-Snowflake (5-page dashboard)
- Snowflake CoCo Desktop (planning, development, execution, testing).
