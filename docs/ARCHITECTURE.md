# Architecture

## Data Pipeline

```mermaid
graph LR
    subgraph RAW["RAW Layer (7 tables)"]
        R1[RAW_CUSTOMERS]
        R2[RAW_POLICIES]
        R3[RAW_CLAIMS]
        R4[RAW_LOANS]
        R5[RAW_INTERACTIONS]
        R6[RAW_CALL_TRANSCRIPTS]
        R7[RAW_DOCUMENTS]
    end

    subgraph CLEAN["CLEAN Layer (6 DTs — DOWNSTREAM)"]
        C1[DT_CUSTOMERS]
        C2[DT_POLICIES]
        C3[DT_CLAIMS]
        C4[DT_LOANS]
        C5[DT_INTERACTIONS]
        C6[DT_CALL_TRANSCRIPTS]
    end

    subgraph CURATED["CURATED Layer (2 DTs — DOWNSTREAM)"]
        CU1[CUSTOMER_360_UNIFIED<br/>7-way aggregation join]
        CU2[CUSTOMER_INTERACTION_TIMELINE<br/>6 UNION ALL event stream]
    end

    subgraph AI["AI Layer (6 DTs — 60 min / 5 min)"]
        A1[DT_TRANSCRIPT_SENTIMENT<br/>CORTEX.SENTIMENT + SUMMARIZE]
        A2[DT_CHURN_RISK<br/>CORTEX.COMPLETE llama3.1-8b]
        A3[DT_NEXT_BEST_ACTION<br/>CORTEX.COMPLETE llama3.1-8b]
        A4[DT_CUSTOMER_HEALTH_SCORE<br/>Composite A-F grade]
        A5[DT_DOCUMENT_PARSED]
        A6[DT_DOCUMENT_EXTRACTED<br/>CORTEX.COMPLETE llama3.1-8b]
    end

    subgraph APP["APP Layer"]
        S1[Semantic View<br/>5 tables, 10 VQRs]
        S2[Cortex Agent<br/>llama3.1-70b]
        S3[Cortex Search<br/>RAG over interactions]
        S4[Streamlit App<br/>10 pages]
        S5[3 Proactive Alerts]
        S6[NBA Email Workflow]
    end

    R1 --> C1
    R2 --> C2
    R3 --> C3
    R4 --> C4
    R5 --> C5
    R6 --> C6

    C1 --> CU1
    C2 --> CU1
    C3 --> CU1
    C4 --> CU1
    C5 --> CU1
    C6 --> CU1

    C1 --> CU2
    C2 --> CU2
    C3 --> CU2
    C4 --> CU2
    C5 --> CU2
    C6 --> CU2

    CU1 --> A2
    CU1 --> A3
    CU1 --> A4
    C6 --> A1
    A1 --> A2
    A2 --> A3

    R7 --> A5
    A5 --> A6
    A6 --> CU2

    A1 --> S3
    CU1 --> S1
    A2 --> S1
    A3 --> S1
    A1 --> S1
    A6 --> S1

    S1 --> S2
    S3 --> S2
    S1 --> S4
    S2 --> S4
    A2 --> S5
    A3 --> S6
```

## Security & Governance

```mermaid
graph TB
    subgraph Governance
        MP1[EMAIL_MASK]
        MP2[PHONE_MASK]
        MP3[FINANCIAL_MASK]
        RAP[REGION_ACCESS_POLICY<br/>Role → Country isolation]
        TAG1[PII_LEVEL tags<br/>HIGH / MEDIUM / LOW]
        TAG2[DATA_DOMAIN tags]
    end

    subgraph Monitoring
        DMF1[CHURN_PARSE_FAILURE_RATE]
        DMF2[NBA_PARSE_FAILURE_RATE]
        VIEW[AI_QUALITY_DASHBOARD]
        AL1[ALERT: High Churn Risk<br/>every 60 min]
        AL2[ALERT: AI Quality<br/>every 6 hours]
        AL3[ALERT: VIP Complaint<br/>every 30 min]
        RM[Resource Monitor<br/>100 credits/month]
    end

    subgraph Security
        SQLi[SQL Injection Prevention<br/>Allowlist sanitization]
        XSS[XSS Prevention<br/>html.escape on all output]
        MASK[Data Masking<br/>PII columns protected]
    end
```

## Cortex AI Functions Used

| Function | Where Used | Purpose |
|----------|-----------|---------|
| `CORTEX.SENTIMENT` | DT_TRANSCRIPT_SENTIMENT | Score call transcripts (-1 to 1) |
| `CORTEX.SUMMARIZE` | DT_TRANSCRIPT_SENTIMENT | Generate 2-3 sentence call summaries |
| `CORTEX.COMPLETE` | DT_CHURN_RISK | Predict churn risk (0-1) with risk factors |
| `CORTEX.COMPLETE` | DT_NEXT_BEST_ACTION | Recommend retention actions |
| `CORTEX.COMPLETE` | DT_DOCUMENT_EXTRACTED | Extract structured fields from documents |
| `CORTEX.COMPLETE` | SP_SEND_NBA_EMAILS | Generate personalized retention emails |
| `CORTEX.COMPLETE` | What-If Simulator | Predict churn under modified conditions |
| `CORTEX.COMPLETE` | AI Advisor (5_AI_Advisor.py) | Conversational customer intelligence |
| `CORTEX.TRANSLATE` | CUSTOMER_SUMMARY_TRANSLATED | Multilingual customer summaries |
| Cortex Search | INTERACTION_SEARCH_SERVICE | Semantic search over interactions |
| Cortex Agent | CUSTOMER_360_AGENT | Orchestrated multi-tool AI advisor |
