# Customer 360 - Next Best Action Engine

Unified insurance and lending customer intelligence powered by Snowflake Cortex AI. Built for the Snowflake CoCo Hackathon.

## Architecture

**Medallion pipeline**: RAW > CLEAN > CURATED > AI > APP

- **ETL**: 6 source tables, 6 CLEAN dynamic tables, 2 CURATED dynamic tables
- **AI Enrichment**: Sentiment analysis (AI_SENTIMENT), Churn risk scoring (AI_COMPLETE), Next Best Action generation (AI_COMPLETE), Cortex Search Service
- **Semantic Model**: 4-table semantic view with 6 verified queries
- **Streamlit App**: 5-page dashboard with Customer 360, Churn Risk, Sentiment, NBA, and AI Advisor chat

## Project Structure

```
sql/                          -- SQL scripts (run in order 00-09)
semantic/                     -- Semantic view YAML definition
streamlit_app/                -- Streamlit-in-Snowflake application
  app.py                      -- Main dashboard
  pages/
    1_Customer_360.py          -- Customer search + unified profile
    2_Churn_Risk.py            -- Churn risk dashboard
    3_Sentiment.py             -- Call sentiment analysis
    4_Next_Best_Action.py      -- NBA recommendations
    5_AI_Advisor.py            -- Cortex Agent chat
```

## Deployment

1. Run SQL scripts 00-09 in order via `python run_pipeline.py`
2. Create semantic view in Snowsight from `semantic/customer_360_semantic.yaml`
3. Deploy Streamlit app: `python deploy_streamlit.py`

## Built With

- Snowflake Cortex AI (AI_SENTIMENT, AI_COMPLETE, SUMMARIZE)
- Snowflake Dynamic Tables
- Cortex Search Service
- Semantic Views + Cortex Analyst
- Streamlit-in-Snowflake
- Snowflake CoCo Desktop
