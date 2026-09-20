# SiS Compatibility Guide

Known issues, constraints, and workarounds for running the Customer 360 app on Streamlit-in-Snowflake (SiS) warehouse runtime.

---

## Runtime Environment

| Property | Value |
|----------|-------|
| Streamlit version | **1.22.0** (pinned by SiS warehouse runtime) |
| Python version | 3.8 |
| Runtime type | Warehouse (not container) |
| Packages available | streamlit, pandas, snowflake-snowpark-python |
| Network access | Blocked (no outbound HTTP from app code) |

The SiS warehouse runtime bundles a fixed Streamlit version that cannot be upgraded. The container runtime (`SYSTEM$ST_CONTAINER_RUNTIME_PY3_11`) runs a newer Streamlit but requires a compute pool and different deployment config.

---

## Known Issues

### 1. `st.rerun()` does not exist (use `st.experimental_rerun()`)

**Error:** `AttributeError: module 'streamlit' has no attribute 'rerun'`

**Cause:** `st.rerun()` was added in Streamlit 1.27.0. The SiS warehouse runtime runs 1.22.0.

**Fix:** Use `st.experimental_rerun()` in all app code. Do not follow current Streamlit documentation that recommends `st.rerun()`.

**Affected files:**
- `app/pages/5_AI_Advisor.py` (sidebar button reruns, clear chat)
- `app/pages/6_Operations.py` (Refresh Data button)

---

### 2. `st.chat_message` / `st.chat_input` not available

**Error:** `AttributeError: module 'streamlit' has no attribute 'chat_message'`

**Cause:** Chat elements were added in Streamlit 1.31.0.

**Workaround:** The AI Advisor page uses `st.text_input` + `st.button("Send")` for input and `st.markdown("**You:** ...")` / `st.markdown("**Assistant:** ...")` for message rendering.

**Affected files:**
- `app/pages/5_AI_Advisor.py`

---

### 3. `st.tabs` not available

**Error:** `AttributeError: module 'streamlit' has no attribute 'tabs'`

**Cause:** `st.tabs` was added in Streamlit 1.23.0 (SiS runs 1.22.0).

**Workaround:** The Customer 360 page uses `st.radio` with horizontal layout to simulate tab navigation.

**Affected files:**
- `app/pages/1_Customer_360.py`

---

### 4. No outbound HTTP from app code

**Error:** Network calls via `urllib.request`, `requests`, or `httplib` are blocked in the SiS sandbox.

**Cause:** The SiS warehouse runtime does not allow outbound network access from Python code.

**Impact:** Cannot call the Cortex Agent REST API (`/api/v2/.../agents/:run`) directly from the app.

**Workaround:** The AI Advisor uses `session.sql("SELECT SNOWFLAKE.CORTEX.AGENT(...)") ` to call the agent via SQL. If the `SNOWFLAKE.CORTEX.AGENT()` function is not available in the account, it falls back to keyword-routed SQL queries and `SNOWFLAKE.CORTEX.COMPLETE()`.

**Affected files:**
- `app/pages/5_AI_Advisor.py`

---

### 5. Private session internals not accessible

**Error:** `AttributeError` when accessing `session._conn._conn.host` or `session._conn._conn.rest.token`

**Cause:** The SiS Snowpark session object does not expose the same internal connection attributes as the local connector.

**Impact:** Cannot extract the auth token or host for REST API calls.

**Workaround:** Use `session.sql()` for all Snowflake operations instead of constructing HTTP requests.

**Affected files:**
- `app/pages/5_AI_Advisor.py` (Cortex Agent call rewritten to use SQL)

---

### 6. `SNOWFLAKE.CORTEX.AGENT()` function not available

**Error:** `SQL compilation error: Unknown user-defined function SNOWFLAKE.CORTEX.AGENT`

**Cause:** The `SNOWFLAKE.CORTEX.AGENT()` SQL function may not be enabled in all Snowflake accounts. It requires the Cortex Agent feature to be provisioned.

**Impact:** The AI Advisor cannot use the Cortex Agent for conversational responses.

**Workaround:** The AI Advisor has a multi-tier fallback:
1. Try `SNOWFLAKE.CORTEX.AGENT()` via SQL
2. If that fails, use keyword-routed SQL queries (covers 7 common question patterns)
3. If no keyword match, fall back to `SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b', ...)` with a domain-scoped prompt

**Affected files:**
- `app/pages/5_AI_Advisor.py`

---

### 7. `st.metric` key parameter behavior

**Symptom:** Health Check page reports `st.metric` test as FAIL.

**Cause:** `st.metric` on SiS 1.22.0 has slightly different parameter handling. The test uses a `key` parameter that triggers an internal error in this version.

**Impact:** Cosmetic only. `st.metric` renders correctly on all dashboard pages (Home, Churn Risk, Sentiment, Operations) when used without a `key` parameter.

**Affected files:**
- `app/pages/0_Health_Check.py` (test artifact, not a bug)

---

## API Compatibility Reference

| API | Added in | SiS 1.22 | Workaround |
|-----|----------|----------|------------|
| `st.rerun()` | 1.27.0 | No | Use `st.experimental_rerun()` |
| `st.chat_message` | 1.31.0 | No | Use `st.markdown` for message rendering |
| `st.chat_input` | 1.31.0 | No | Use `st.text_input` + `st.button` |
| `st.tabs` | 1.23.0 | No | Use `st.radio` with horizontal layout |
| `st.dataframe(use_container_width)` | 1.18.0 | Yes | Works |
| `st.columns` | 1.0.0 | Yes | Works |
| `st.metric` | 1.13.0 | Yes | Works (avoid `key` param in tests) |
| `st.expander` | 1.0.0 | Yes | Works |
| `st.set_page_config` | 1.0.0 | Yes | Works |
| `st.session_state` | 1.12.0 | Yes | Works |
| `st.bar_chart` | 1.0.0 | Yes | Works |
| `st.spinner` | 1.0.0 | Yes | Works |
| `st.markdown(unsafe_allow_html)` | 1.0.0 | Yes | Works |

---

## Migrating to Container Runtime

To use newer Streamlit APIs, migrate to the container runtime:

1. Update `snowflake.yml`:
```yaml
definition_version: 2
entities:
  customer_360_app:
    type: streamlit
    identifier:
      name: CUSTOMER_360_APP
      schema: APP
      database: CUSTOMER_360
    query_warehouse: COMPUTE_WH
    runtime_name: SYSTEM$ST_CONTAINER_RUNTIME_PY3_11
    compute_pool: <YOUR_COMPUTE_POOL>
    external_access_integrations:
      - <PYPI_ACCESS_INTEGRATION>
    main_file: app.py
    artifacts:
      - app.py
      - pages/
      - pyproject.toml
```

2. Replace `environment.yml` with `pyproject.toml` dependencies
3. Replace `st.experimental_rerun()` with `st.rerun()`
4. Optionally replace `st.radio` tab workarounds with `st.tabs`
5. Optionally replace `st.text_input`+`st.button` with `st.chat_input`+`st.chat_message`

---

## Browser Test Results (2026-09-20)

All 8 pages tested via Playwright browser automation against the live SiS deployment.

| Page | Status | Notes |
|------|--------|-------|
| Home | PASS | KPIs (2,000 customers, 1,649 active, 2 high risk), charts, action table |
| Health Check | PASS* | st.metric test fails (SiS 1.22 limitation), all other tests pass |
| Customer 360 | PASS | Search works ("Joshua White" found, ID 515899) |
| Churn Risk | PASS | Segment filters, risk slider, data table |
| Sentiment | PASS | Charts, transcript viewer, 1,000 calls analyzed |
| Next Best Action | PASS | Priority/type filters, 2,000 recommendations |
| AI Advisor | PASS* | CORTEX.AGENT unavailable; SQL fallback works ("6 customers with >2 complaints") |
| Operations | PASS | Layer counts, DT health, Refresh Data button works (st.experimental_rerun confirmed) |
