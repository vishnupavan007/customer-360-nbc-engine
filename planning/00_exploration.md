# Planning Phase: CoCo-Driven Exploration

These are the CoCo CLI commands used during the planning phase to explore the
problem space, profile the data, and validate the solution design before any
pipelines or application code was written.

## 1. Problem framing with Cortex Complete

```bash
snow cortex complete \
  --connection ivvnigo-ds76948 \
  --query "Design a data model for a unified Customer 360 platform in insurance
  and lending. The platform needs to track churn risk, next best action, call
  sentiment, and document intelligence. Suggest a medallion architecture with
  RAW, CLEAN, CURATED, and AI layers. Include what Snowflake features to use at
  each layer." \
  --model llama3.1-70b
```

Key output that shaped the architecture:
- **RAW**: landing tables, no transformation, append-only inserts
- **CLEAN**: Dynamic Tables with deduplication and normalization
- **CURATED**: Dynamic Tables joining 6 domains into a unified 360 record
- **AI**: Dynamic Tables calling CORTEX.COMPLETE for churn risk, NBA, and sentiment;
  Cortex Search for interaction history
- **APP**: Semantic View for Cortex Analyst + Streamlit for human-readable access

## 2. Domain ontology with Cortex Complete

```bash
snow cortex complete \
  --connection ivvnigo-ds76948 \
  --query "For an insurance and lending Customer 360 platform, list the key
  entities, their attributes, and how they relate. Focus on: customers,
  policies, claims, loans, interactions, and call transcripts." \
  --model llama3.1-70b
```

This shaped the RAW table schema in `pipeline/schema/01_raw_tables.sql`.

## 3. Synthetic data design

```bash
snow cortex complete \
  --connection ivvnigo-ds76948 \
  --query "Generate a SQL INSERT statement for 5 realistic insurance customers
  with fields: customer_id, full_name, email, segment (Premium/Standard/Basic/Enterprise),
  country, tenure_months, complaint_count, created_at." \
  --model llama3.1-70b
```

Used to validate the synthetic data format before writing
`pipeline/data/02_synthetic_data.sql` (3,450+ rows).

## 4. AI prompt engineering for churn and NBA

```bash
snow cortex complete \
  --connection ivvnigo-ds76948 \
  --query "Write a JSON-output prompt for an LLM that assesses churn risk for
  an insurance customer. Input: customer segment, tenure months, complaint count,
  claim count. Output JSON: { churn_risk_score: float 0-1, risk_factors: [],
  retention_urgency: string, confidence: float }." \
  --model llama3.1-70b
```

The resulting prompt template was used in `pipeline/ai/05_ai_enrichment.sql`
for `DT_CHURN_RISK` and `DT_NEXT_BEST_ACTION`.

## 5. Semantic model question set

Used CoCo Desktop chat to enumerate what questions business users would ask:

```
"Which customers are most at risk of churning this month?"
"What is the recommended next action for customer John Smith?"
"How many Premium customers have open claims and high churn risk?"
"What is the average call sentiment score by segment?"
"Which customers with recent complaints have not been contacted?"
```

Each question was used as a Verified Query in `serving/semantic_model/customer_360_semantic.yaml`.

## 6. Post-build validation via pipeline health skill

After deployment, ran the full 23-test validation suite through CoCo Desktop:

```
/pipeline-health-snapshot
```

Result: HEALTHY — all 23 tests passing, 500+ customers in pipeline.

## Summary

CoCo was used at every planning step — problem framing, schema design, data
generation templates, AI prompt engineering, semantic model VQRs, and final
validation — before writing a single line of production code.
