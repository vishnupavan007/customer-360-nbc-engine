# Streamlit-in-Snowflake (SiS) Compatibility Guide

This project deploys to **SiS warehouse runtime** which runs **Streamlit 1.22.0**. This guide documents known API limitations and the workarounds used.

## Runtime Environment

| Property | Value |
|---|---|
| Runtime | Warehouse (not Container) |
| Streamlit version | 1.22.0 |
| Python version | 3.8 |
| Session | `get_active_session()` from `snowflake.snowpark.context` |
| Network | No outbound HTTP from sandbox |

## API Compatibility

| API | Available | Workaround Used |
|---|---|---|
| `st.rerun()` | No (added in 1.27) | `st.experimental_rerun()` |
| `st.tabs()` | No (added in 1.23) | `st.radio()` with horizontal layout |
| `st.chat_input()` | No (added in 1.23) | `st.form()` + `st.text_input()` + submit button |
| `st.chat_message()` | No (added in 1.23) | Custom HTML bubbles via `st.markdown(unsafe_allow_html=True)` |
| `st.cache_data` | Yes | Used with `ttl=300` on all query functions |
| `st.cache_resource` | Yes | Not currently used |
| `st.bar_chart` | Yes | Used for standard charts |
| `st.line_chart` | Yes | Used for trend charts |
| `st.plotly_chart` | Yes (if plotly in env) | Import guard with `st.bar_chart` fallback |
| `st.expander` | Yes | Avoid nesting (nested expanders crash) |
| `st.form` | Yes | Used for AI Advisor input |
| `st.download_button` | Yes | Used for CSV export |

## Known Limitations

### 1. No outbound HTTP
The SiS sandbox blocks `urllib.request`, `requests`, and any outbound network calls. The Cortex Agent REST API is not accessible. Workaround: use `SNOWFLAKE.CORTEX.COMPLETE()` via `session.sql()`.

### 2. Private Snowpark internals
`session._conn._conn` is not accessible in SiS. Do not use private APIs to extract host, token, or connection details.

### 3. Nested expanders
`st.expander` inside another `st.expander` crashes on SiS 1.22. Keep expanders at one level of nesting.

### 4. Module imports
Custom modules (like `utils.py`) must be uploaded to the SiS stage alongside the app files. Missing modules cause `ModuleNotFoundError` at runtime.

### 5. Package availability
Only packages listed in `environment.yml` are available. The Snowflake conda channel has a limited package set. Check availability before adding imports.

## Files Affected by SiS Workarounds

| File | Workaround |
|---|---|
| `utils.py` | `st.experimental_rerun()` for theme toggle |
| `pages/5_AI_Advisor.py` | Form-based chat input, SQL-based CORTEX.COMPLETE instead of REST Agent |
| `pages/6_Operations.py` | `st.experimental_rerun()` for refresh button |
| `pages/1_Customer_360.py` | `st.radio()` instead of `st.tabs()` for profile sections |
| `pages/4_Next_Best_Action.py` | Plotly import guard with `st.bar_chart` fallback |

## Migration to Container Runtime

When migrating to SiS container runtime (`SYSTEM$ST_CONTAINER_RUNTIME_PY3_11`):
1. Replace `st.experimental_rerun()` with `st.rerun()`
2. Replace `st.radio()` tabs with `st.tabs()`
3. Replace form-based chat with `st.chat_input()` + `st.chat_message()`
4. Can use REST API for Cortex Agent (outbound HTTP available)
5. More packages available via pip
