---
name: pipeline-health-snapshot
description: Run the 23-test Customer 360 validation suite and return a formatted pipeline health report with layer row counts and AI quality log status.
---

# Pipeline Health Snapshot

## Purpose

Give the operations team an instant view of pipeline health: test pass/fail results, row counts per medallion layer, dynamic table refresh status, and the latest AI quality monitoring results.

## Instructions

1. Run the full 23-test validation suite:

```sql
CALL CUSTOMER_360.APP.RUN_APP_TESTS();
```

2. Get row counts for each pipeline layer:

```sql
SELECT 'RAW › Customers'        AS layer, COUNT(*) AS rows FROM CUSTOMER_360.RAW.RAW_CUSTOMERS        UNION ALL
SELECT 'RAW › Policies',                  COUNT(*) FROM CUSTOMER_360.RAW.RAW_POLICIES                UNION ALL
SELECT 'RAW › Claims',                    COUNT(*) FROM CUSTOMER_360.RAW.RAW_CLAIMS                  UNION ALL
SELECT 'RAW › Loans',                     COUNT(*) FROM CUSTOMER_360.RAW.RAW_LOANS                   UNION ALL
SELECT 'RAW › Interactions',              COUNT(*) FROM CUSTOMER_360.RAW.RAW_INTERACTIONS             UNION ALL
SELECT 'RAW › Transcripts',               COUNT(*) FROM CUSTOMER_360.RAW.RAW_CALL_TRANSCRIPTS         UNION ALL
SELECT 'CLEAN › Customers',               COUNT(*) FROM CUSTOMER_360.CLEAN.DT_CUSTOMERS               UNION ALL
SELECT 'CURATED › Unified',               COUNT(*) FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED     UNION ALL
SELECT 'AI › Churn Risk',                 COUNT(*) FROM CUSTOMER_360.AI.DT_CHURN_RISK                 UNION ALL
SELECT 'AI › Next Best Action',           COUNT(*) FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION           UNION ALL
SELECT 'AI › Sentiment',                  COUNT(*) FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT       UNION ALL
SELECT 'AI › Documents Extracted',        COUNT(*) FROM CUSTOMER_360.AI.DT_DOCUMENT_EXTRACTED
ORDER BY 1;
```

3. Get the latest AI quality log entries:

```sql
SELECT
    CHECK_TYPE,
    METRIC_NAME,
    METRIC_VALUE,
    THRESHOLD,
    STATUS,
    CHECK_TIMESTAMP
FROM CUSTOMER_360.APP.AI_QUALITY_LOG
ORDER BY CHECK_TIMESTAMP DESC
LIMIT 10;
```

4. Format the response as:

**Overall Status**
- HEALTHY (all tests pass + all quality checks PASS)
- DEGRADED (some tests fail OR quality checks FAIL)
- FAILING (>5 test failures)

**Test Results**
- X / 23 tests passed
- If any failed: list each failure with TEST_NAME and DETAIL

**Layer Row Counts** (table)

**AI Quality Checks** (last 10 entries, highlight any FAIL in red)

**Recommendations**
- If DEGRADED or FAILING: suggest which layer or test to investigate first
- If HEALTHY: confirm pipeline is operating normally and state the total customer count
