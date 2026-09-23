---
name: customer-360-snapshot
description: Pull a complete Customer 360 profile for any customer — churn risk, next best action, call sentiment, and policy summary. Works against the CUSTOMER_360 database.
---

# Customer 360 Snapshot

## Purpose

Retrieve and summarize the complete intelligence profile for a given customer: churn risk score and top risk factors, next best action recommendation, recent call sentiment trend, and policy/loan overview.

## Instructions

1. If no customer name or ID was provided in the command, ask: **"Which customer? Provide a name or customer ID."**

2. Query the customer profile:

```sql
SELECT
    c.CUSTOMER_ID,
    c.FULL_NAME,
    c.SEGMENT,
    c.COUNTRY,
    c.TENURE_MONTHS,
    c.TOTAL_POLICIES,
    c.TOTAL_CLAIMS,
    c.COMPLAINT_COUNT,
    r.CHURN_RISK_SCORE,
    r.RISK_FACTORS,
    r.RETENTION_URGENCY,
    r.CONFIDENCE,
    n.ACTION_TYPE,
    n.ACTION_DESCRIPTION,
    n.PRIORITY,
    n.CHANNEL,
    n.RATIONALE
FROM CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c
LEFT JOIN CUSTOMER_360.AI.DT_CHURN_RISK r ON r.CUSTOMER_ID = c.CUSTOMER_ID
LEFT JOIN CUSTOMER_360.AI.DT_NEXT_BEST_ACTION n ON n.CUSTOMER_ID = c.CUSTOMER_ID
WHERE LOWER(c.FULL_NAME) LIKE LOWER('%<NAME>%')
   OR c.CUSTOMER_ID = '<ID>'
LIMIT 1;
```

3. Query their sentiment trend:

```sql
SELECT
    AVG(SENTIMENT_SCORE)  AS AVG_SENTIMENT,
    MIN(SENTIMENT_SCORE)  AS MIN_SENTIMENT,
    COUNT(*)              AS TOTAL_CALLS,
    SUM(CASE WHEN SENTIMENT_LABEL = 'Negative' THEN 1 ELSE 0 END) AS NEGATIVE_CALLS
FROM CUSTOMER_360.AI.DT_TRANSCRIPT_SENTIMENT
WHERE CUSTOMER_ID = '<CUSTOMER_ID>'
LIMIT 1;
```

4. Format the response with these sections:

**Customer Profile**
- Name, Segment, Country, Tenure (months)
- Policies: `TOTAL_POLICIES` active, `TOTAL_CLAIMS` claims filed, `COMPLAINT_COUNT` complaints

**Churn Risk** — colour-code the score:
- >= 0.7 = **HIGH RISK**
- 0.4–0.69 = **MEDIUM RISK**
- < 0.4 = **LOW RISK**
- List the top 2 risk factors from `RISK_FACTORS`
- State retention urgency and model confidence

**Next Best Action**
- Action type and full description
- Recommended channel and priority level
- One-sentence rationale

**Call Sentiment**
- Average sentiment score and call count
- Flag if more than 30% of calls are negative

**Action Summary**
- One actionable sentence for the account team
