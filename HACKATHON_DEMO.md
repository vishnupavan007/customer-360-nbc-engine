# Hackathon Demo Guide

Operational reference for all CoCo demo phases: planning, automation, Slack MCP, skill publishing, and cross-surface demo.

---

## Phase 1 — Planning: CoCo-Driven Exploration Before Build

Show that CoCo was used to explore the problem space and design the solution before any code was written.

### Step 1: Explore schema with CoCo CLI

```bash
# Discover what tables exist in the raw layer
snow sql --connection ivvnigo-ds76948 -q "SHOW TABLES IN SCHEMA CUSTOMER_360.RAW"

# Profile a key table
snow sql --connection ivvnigo-ds76948 -q "SELECT COUNT(*), MIN(CREATED_AT), MAX(CREATED_AT) FROM CUSTOMER_360.RAW.RAW_CUSTOMERS"
```

### Step 2: Frame the problem with Cortex Complete

```bash
snow cortex complete \
  --connection ivvnigo-ds76948 \
  --query "Design a data model for a unified Customer 360 platform in insurance and lending. The platform needs to track churn risk, next best action, call sentiment, and document intelligence. Suggest a medallion architecture with RAW, CLEAN, CURATED, and AI layers." \
  --model llama3.1-70b
```

### Step 3: Validate the semantic model with natural language

After the semantic view is deployed, confirm the model answers planning questions:

```bash
# Via CoCo Desktop chat:
"What are the top 5 customers by churn risk and their recommended next actions?"
"How many Premium customers have open claims and a churn score above 0.7?"
"What is the average sentiment score by customer segment?"
```

### Step 4: Verify everything is working with the pipeline health skill

```bash
# Run the published skill from CoCo Desktop chat:
/pipeline-health-snapshot
```

Expected: HEALTHY status with all 23 tests passing.

---

## Phase 4 — CoCo Automation: Daily Churn Alert

Schedule an unattended daily digest that runs every weekday morning via CoCo CLI.

### Create the automation

```bash
cortex automation create \
  --name "daily_churn_alert" \
  --schedule "0 9 * * 1-5" \
  --prompt "Run the pipeline-health-snapshot skill and then find any customers whose churn risk score is above 0.8 in CUSTOMER_360.AI.DT_CHURN_RISK. Join to CUSTOMER_360.AI.DT_NEXT_BEST_ACTION. List the top 5 highest-risk customers with their name, segment, churn score, and next best action. Format as a brief daily digest with a one-line status summary at the top."
```

### Manage the automation

```bash
# List all automations
cortex automation list

# View run logs
cortex automation logs daily_churn_alert

# Pause / resume
cortex automation suspend daily_churn_alert
cortex automation resume  daily_churn_alert

# Delete
cortex automation delete daily_churn_alert
```

### Upgrade: post digest to Slack (after Phase 5 MCP is configured)

```bash
cortex automation update daily_churn_alert \
  --prompt "Run the pipeline-health-snapshot skill. Then query CUSTOMER_360.AI.DT_CHURN_RISK joined to CUSTOMER_360.AI.DT_NEXT_BEST_ACTION and find the top 5 customers with churn score > 0.8. Post the results as a formatted daily digest to the Slack channel #customer-360-alerts. Include today's date in the sign-off."
```

---

## Phase 5 — Slack MCP Connector

Connect CoCo Desktop to Slack so the Cortex Agent can post NBA alerts directly to a channel.

### Step 1: Create a Slack app

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps) → **Create New App > From scratch**
2. Name: `Customer360-CoCo-Alerts` | choose your workspace
3. Under **OAuth & Permissions > Bot Token Scopes**, add:
   - `chat:write`
   - `channels:read`
   - `channels:join`
4. Click **Install to Workspace** → copy the **Bot User OAuth Token** (`xoxb-...`)
5. Note your **Team ID** (visible in the workspace URL: `app.slack.com/client/TXXXXXXXX`)
6. In Slack, create channel `#customer-360-alerts` and invite the bot: `/invite @Customer360-CoCo-Alerts`

### Step 2: Configure MCP in CoCo Desktop

The credentials are stored in `.env` (gitignored).

CoCo Desktop requires a **remote (SSE/HTTP) URL** for MCP servers — it does not run local stdio processes directly. Use `supergateway` to bridge the Slack MCP stdio server to an SSE endpoint.

**Step 2a — Start the local MCP bridge (keep this terminal open before every demo):**

Open a new PowerShell terminal and run:

```powershell
$env:SLACK_BOT_TOKEN="xoxb-YOUR-SLACK-BOT-TOKEN"
$env:SLACK_TEAM_ID="T0C3X6E9W3Y"
npx -y supergateway --stdio "npx -y @modelcontextprotocol/server-slack" --port 8808
```

Wait until you see `Listening on port 8808`. Leave the terminal open.

**Step 2b — Add the server in CoCo Desktop:**

1. Open **CoCo Desktop → Settings → MCP Servers → Add server**
2. Enter URL: `http://localhost:8808`
3. Click **Save** and restart CoCo Desktop.

Slack tools (`slack_post_message`, `slack_list_channels`) will appear in the tool list.

4. Verify by asking CoCo: `"List my Slack channels"` — it should return the available channels including `#customer-360-alerts`.


### Step 3: Test the integration

Ask CoCo Desktop:

> "Find the 3 customers with the highest churn risk scores right now and send a summary to the #customer-360-alerts Slack channel. Include each customer's name, segment, churn score, and recommended next best action."

CoCo will:
1. Query `CUSTOMER_360.AI.DT_CHURN_RISK` and `DT_NEXT_BEST_ACTION` via Snowflake
2. Format a Slack message
3. Call the `slack_post_message` MCP tool to post it

### Demo prompts

```
"Post the top 5 Premium customers at churn risk to #customer-360-alerts"

"Send a Slack alert for any customer with a complaint in the last 30 days
 and a churn score above 0.7"

"Post a summary of today's NBA queue to #customer-360-alerts —
 include total count by action type and the top 3 high-priority customers"
```

---

## Phase 6 — Cross-Surface Demo Script

The Cortex Agent `CUSTOMER_360.APP.CUSTOMER_360_AGENT` works identically across all three surfaces. No code changes needed.

### Surface 1: CoCo Desktop (chat panel)

Type directly in the chat:

```
"Which Premium customers have a churn risk above 0.7 and what is their
 recommended next action?"

"Show me the top 5 customers with open claims and high churn risk"

"What is the average sentiment score by customer segment?"
```

### Surface 2: CoCo CLI (terminal)

```bash
# Direct Cortex complete
snow cortex complete \
  --query "Which customers in the Premium segment have the highest churn risk?" \
  --model llama3.1-70b

# Via the Cortex Agent
cortex agent run CUSTOMER_360.APP.CUSTOMER_360_AGENT \
  --prompt "Show me the top 5 churners in the Premium segment with their NBA"

# Run a skill from CLI
cortex skill run customer-360-snapshot --input "Joshua White"
```

### Surface 3: Snowsight Cloud Agents

1. Go to **AI & ML > Cortex Agents** in Snowsight
2. Open `CUSTOMER_360.APP.CUSTOMER_360_AGENT`
3. Ask:
   - "Which customers have open claims and a churn risk above 0.6?"
   - "What are the most common next best actions for customers with negative sentiment?"
   - "How many high-risk churn customers are in the Premium segment?"

### Demo comparison table

| Surface | Command/Location | Best for |
|---------|-----------------|---------|
| CoCo Desktop | Chat panel | Interactive exploration, skill invocation |
| CoCo CLI | `cortex agent run` | Scripting, automation, CI/CD |
| Snowsight Cloud Agents | AI & ML > Cortex Agents | Business user demos, no-code access |

All three hit the same `CUSTOMER_360_AGENT` backed by `Customer360SemanticView` + `INTERACTION_SEARCH_SERVICE`, producing consistent answers.

---

## Hackathon Criteria Coverage Summary

| Criterion | How demonstrated |
|-----------|-----------------|
| Synthetic data | `SP_DAILY_SYNTHETIC_DATA` + `TASK_DAILY_RAW_INGEST` (daily midnight UTC) |
| Data pipeline | 13 dynamic tables, medallion architecture, 5 quality monitoring tasks |
| Semantic model | `Customer360SemanticView` with 9 verified Cortex Analyst queries |
| Streamlit app | 7-page SiS app at `CUSTOMER_360.APP.CUSTOMER_360_APP` |
| Document processing | `DT_DOCUMENT_EXTRACTED` (CORTEX.COMPLETE), `INTERACTION_SEARCH_SERVICE` |
| MCP connectors | Slack MCP — Phase 5 above |
| Reusable skills | `customer-360-snapshot`, `nba-campaign-report`, `pipeline-health-snapshot` |
| Automations | `daily_churn_alert` automation — Phase 4 above |
| Cross-surface | CoCo Desktop / CoCo CLI / Snowsight Cloud Agents — Phase 6 above |
| Guardrails | AI Advisor 3-tier routing, domain guard, `RUN_APP_TESTS()` 23-test suite |
