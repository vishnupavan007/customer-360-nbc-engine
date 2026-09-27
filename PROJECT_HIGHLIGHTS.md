# Project Highlights

## Customer 360 — Next Best Action Engine

> AI-powered unified customer intelligence for insurance and lending, built entirely on Snowflake.

---

### By the Numbers

| Metric | Count |
|--------|-------|
| Streamlit Pages | 10 |
| Dynamic Tables | 14 |
| Cortex AI Functions Used | 7 (SENTIMENT, SUMMARIZE, COMPLETE, TRANSLATE, Cortex Search, Cortex Agent, Semantic View) |
| SQL Test Suite | 33 tests, all PASS |
| Proactive Alerts | 3 (churn risk, AI quality, VIP complaints) |
| Masking Policies | 3 (email, phone, financial) |
| Data Metric Functions | 2 (churn + NBA parse failure monitoring) |
| Verified Queries | 10 (Cortex Analyst) |
| Synthetic Data | 2,000 customers, 8,268 timeline events, 20 documents |
| CoCo Skills | 3 reusable skills |

---

### Snowflake Feature Coverage

| Category | Features Used |
|----------|-------------|
| **Data Pipeline** | Dynamic Tables (14), medallion architecture (RAW→CLEAN→CURATED→AI→APP), DOWNSTREAM + fixed lag |
| **Cortex AI** | SENTIMENT, SUMMARIZE, COMPLETE (llama3.1-8b for scoring, llama3.1-70b for agent), TRANSLATE |
| **Cortex Agent** | CUSTOMER_360_AGENT with semantic view + cortex search tools |
| **Cortex Search** | INTERACTION_SEARCH_SERVICE (semantic search over call transcripts + interactions) |
| **Cortex Analyst** | Semantic View with 5 tables, 10 verified queries |
| **Streamlit in Snowflake** | 10-page app with dark/light theme, SiS 1.22 compatible |
| **Security** | Masking policies, row access policy, PII tags, SQL injection prevention, XSS prevention |
| **Monitoring** | Data Metric Functions, AI_QUALITY_DASHBOARD view, 3 proactive Alerts with email |
| **Automation** | Daily data ingestion task, 5 quality monitoring tasks, NBA email workflow |
| **Cost Management** | Resource monitor (100 credit/month), optimized TARGET_LAG (60 min on AI tables) |
| **CI/CD** | GitHub Actions for Streamlit deployment |
| **CoCo Integration** | 3 skills, Slack MCP connector, automation support |
| **Document Intelligence** | AI extraction from insurance documents, cross-referenced to Customer 360 |

---

### Unique Differentiators

1. **What-If Simulator** — Interactive churn prediction. Adjust customer parameters (premium discount, resolve claims, outreach) and see AI-predicted risk change in real-time.

2. **Customer Health Score** — Composite A-F grade from 5 weighted factors (retention 30%, payment 20%, sentiment 20%, claims 15%, loyalty 15%). Business-friendly alternative to raw churn probability.

3. **Automated NBA→Email** — End-to-end workflow: detect high-risk customers → generate personalized retention emails via CORTEX.COMPLETE → log for audit → notify ops team. Closes the loop from insight to action.

4. **Proactive Alerts** — Platform self-monitors. Critical churn risk, AI quality degradation, and VIP complaints trigger automated email notifications — no human needs to check the dashboard.

5. **Multilingual Support** — CORTEX.TRANSLATE generates customer intelligence summaries in Spanish, French, Japanese, or any supported language.

6. **Full Governance Stack** — Masking policies on PII, row access policies for regional isolation, PII classification tags, Data Metric Functions for AI output quality, and a resource monitor for cost control.

---

### Architecture

See `docs/ARCHITECTURE.md` for Mermaid diagrams showing:
- Complete data pipeline flow (RAW → CLEAN → CURATED → AI → APP)
- Security and governance architecture
- Cortex AI functions map
