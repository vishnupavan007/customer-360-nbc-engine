# Contributing

## Getting Started

1. Clone the repo
2. Copy `.env.example` to `.env` and fill in your Snowflake credentials
3. Run `python scripts/run_pipeline.py` to set up the database and pipeline
4. Run `python scripts/deploy_streamlit.py` to deploy the Streamlit app

## Development

- **SQL changes**: Edit files in `pipeline/`, `serving/`, or `ops/`, then re-run the relevant script via `snowflake-connector-python`
- **Streamlit changes**: Edit files in `app/`, then deploy with `snow streamlit deploy --replace` or `python scripts/deploy_streamlit.py`
- **Skills**: Edit `.snowflake/cortex/skills/*.md` files — they're picked up by CoCo Desktop automatically

## Branch Naming

| Prefix | Use for |
|--------|---------|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `security/` | Security patches |
| `perf/` | Performance improvements |
| `docs/` | Documentation only |
| `test/` | Test additions/changes |
| `ops/` | Operational tooling |

## PR Guidelines

- One feature per PR for easy tracking and review
- Include a "Why this matters" section in the PR body
- Include a test plan with checkboxes
- Reference the relevant Snowflake objects created/modified

## Testing

Run the SQL test suite:
```sql
CALL CUSTOMER_360.APP.RUN_APP_TESTS();
```
Expected: 33/33 PASS.

## SiS Compatibility

See `SIS_COMPATIBILITY.md` for Streamlit 1.22.0 API limitations and workarounds.
