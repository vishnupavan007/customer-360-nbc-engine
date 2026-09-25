# Start Slack MCP bridge for CoCo Desktop
# Run this script once before any demo session that uses the Slack MCP.
# Keep the PowerShell window open — closing it stops the bridge.

# Refresh PATH so Node.js is found even in a fresh terminal
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")

# Slack credentials
$env:SLACK_BOT_TOKEN = $env:SLACK_BOT_TOKEN  # set this in your environment or .env before running
$env:SLACK_TEAM_ID   = "T0C3X6E9W3Y"

Write-Host "Starting Slack MCP bridge on http://localhost:8808 ..."
Write-Host "Leave this window open. Press Ctrl+C to stop."
Write-Host ""

npx -y supergateway --stdio "npx -y @modelcontextprotocol/server-slack" --port 8808
