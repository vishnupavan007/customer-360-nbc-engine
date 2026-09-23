---
name: nba-campaign-report
description: Generate a prioritized Next Best Action campaign list for a customer segment, action type, or priority level. Works against the CUSTOMER_360 database.
---

# NBA Campaign Report

## Purpose

Build a ranked, actionable campaign list from the Next Best Action pipeline so sales and operations teams know exactly who to contact, what to offer, and which channel to use.

## Instructions

1. If no filter was specified, default to **HIGH priority** actions across all segments.

2. Ask which filter to apply if the user wants to narrow down:
   - **Segment**: Premium, Standard, Basic, or Enterprise
   - **Action type**: Retention_Offer, Policy_Review, Claims_Followup, Upsell, Payment_Assistance, Proactive_Outreach, Renewal_Reminder, Complaint_Resolution
   - **Priority**: High, Medium, or Low

3. Run the campaign query:

```sql
SELECT
    n.CUSTOMER_ID,
    c.FULL_NAME,
    c.SEGMENT,
    c.COUNTRY,
    n.ACTION_TYPE,
    n.ACTION_DESCRIPTION,
    n.CHANNEL,
    n.PRIORITY,
    n.RATIONALE,
    r.CHURN_RISK_SCORE
FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION n
JOIN CUSTOMER_360.CURATED.CUSTOMER_360_UNIFIED c ON c.CUSTOMER_ID = n.CUSTOMER_ID
LEFT JOIN CUSTOMER_360.AI.DT_CHURN_RISK r ON r.CUSTOMER_ID = n.CUSTOMER_ID
WHERE n.PRIORITY = '<PRIORITY>'        -- replace filter as needed
ORDER BY r.CHURN_RISK_SCORE DESC NULLS LAST
LIMIT 25;
```

4. Run summary counts:

```sql
SELECT
    ACTION_TYPE,
    CHANNEL,
    COUNT(*) AS CUSTOMER_COUNT
FROM CUSTOMER_360.AI.DT_NEXT_BEST_ACTION
WHERE PRIORITY = '<PRIORITY>'
GROUP BY 1, 2
ORDER BY 3 DESC;
```

5. Format the response as:

**Campaign Summary**
- Total customers in this campaign batch
- Breakdown by action type (table: Action Type | Count)
- Breakdown by channel (table: Channel | Count)

**Top 10 Priority Contacts** (table: Name | Segment | Action | Channel | Churn Risk)

**Campaign Brief** (one paragraph)
- Who to target (segment, risk profile)
- What to offer (dominant action type)
- Which channel to lead with (highest-count channel)
- Expected outcome (retention / upsell / service recovery)
