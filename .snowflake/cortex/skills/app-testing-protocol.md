---
name: app-testing-protocol
description: Mandatory UI testing protocol for the Customer 360 Streamlit app. Run after EVERY code change deployed to SiS. Covers regression testing (existing pages) and feature testing (new pages).
---

# App Testing Protocol

## When to Run

**MANDATORY** after ANY of these events:
- New page added to the app
- Existing page modified (Python code)
- utils.py changed (affects all pages)
- Any file uploaded to @CUSTOMER_360.APP.STREAMLIT_FINAL_STAGE

## Step 1: SQL Test Suite

Run the 33-test validation suite first — this verifies the data layer:

```sql
CALL CUSTOMER_360.APP.RUN_APP_TESTS();
```

Expected: 33/33 PASS. If any fail, fix the data issue before UI testing.

## Step 2: UI Browser Testing

Open the live app and test EVERY page. For each page:
1. Navigate to the page via sidebar
2. Wait for full load (no spinners)
3. Verify key elements render (headings, KPIs, charts, tables)
4. Check browser console for errors
5. Test at least one interactive element (button, filter, search)

### Page-by-Page Checklist

| # | Page | Verify these elements | Test this interaction |
|---|------|----------------------|---------------------|
| 1 | Home (app.py) | Title, 5 KPI metrics, 2 charts, action items table | Scroll to see all sections |
| 2 | Customer 360 | Title, search box, segments table | Search "smith" — expect 14+ results |
| 3 | Churn Risk | Title, KPIs, segment filters, 2 charts, detail table | Change segment filter |
| 4 | Sentiment | Title, date inputs, 4 charts, transcript viewer | Select a date range |
| 5 | Next Best Action | Title, KPIs, Plotly charts, action queue | Change priority filter |
| 6 | AI Advisor | Title, LIVE badge, chat input, suggestion chips | Click a suggestion chip |
| 7 | Operations | Title, refresh button, 5 data tables | Click Refresh Data |
| 8 | Documents | Title, 3 KPIs, extracted fields, viewer, cross-reference | Change document type filter |
| 9 | What-If Simulator | Title, search box, instructions | Search a customer name |
| 10 | Data Lineage | Title, architecture diagram, layer counts, governance, AI quality | Scroll through all sections |

## Step 3: Report Results

Format results as a summary table:

```
| Page | Status | Elements Verified | Errors Found |
|------|--------|-------------------|-------------|
| Home | PASS | KPIs, charts, table | None |
| ... | ... | ... | ... |
```

## Known SiS Limitations

Do NOT use these in the app — they fail in SiS 1.22 warehouse runtime:
- `st.rerun()` — use `st.experimental_rerun()` instead
- `st.tabs()` — use `st.radio()` instead
- `st.chat_input()` / `st.chat_message()` — use `st.form()` + `st.text_input()`
- `st.download_button` — fails due to S3 CORS in iframe. Use `st.dataframe` built-in export
- `session._conn._conn` / `urllib.request` — blocked in sandbox. Use `session.sql()` with CORTEX functions
- Nested `st.expander` — crashes on SiS 1.22

See `SIS_COMPATIBILITY.md` for full details.
