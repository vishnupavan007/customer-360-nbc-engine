"""Deploy Streamlit app to Snowflake using snow CLI, reading credentials from .env"""
import os
import subprocess
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

account = os.getenv("SNOWFLAKE_ACCOUNT")
user = os.getenv("SNOWFLAKE_USER")
password = os.getenv("SNOWFLAKE_PASSWORD")
role = os.getenv("SNOWFLAKE_ROLE")
warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")

if not all([account, user, password]):
    raise ValueError("Missing required env vars: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD")

# Build env with password as environment variable (not CLI arg -- avoids process list exposure)
env = os.environ.copy()
env["SNOWFLAKE_PASSWORD"] = password

# Configure snow CLI connection using env var for password
print("Configuring snow CLI connection...")
add_cmd = [
    "snow", "connection", "add",
    "--connection-name", "default",
    "--account", account,
    "--user", user,
    "--role", role,
    "--warehouse", warehouse,
    "--database", "CUSTOMER_360",
    "--schema", "APP",
    "--no-interactive",
]
result = subprocess.run(add_cmd, capture_output=True, text=True, env=env)
if result.returncode == 0:
    print("Connection configured.")
else:
    print(f"Note: {result.stderr.strip() or result.stdout.strip()}")

# Set as default
subprocess.run(["snow", "connection", "set-default", "default"], capture_output=True, text=True, env=env)

# Deploy the Streamlit app
print("\nDeploying Streamlit app...")
deploy_cmd = ["snow", "streamlit", "deploy", "--replace"]
deploy_result = subprocess.run(
    deploy_cmd,
    cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), "streamlit_app"),
    capture_output=True,
    text=True,
    env=env,
)
print(deploy_result.stdout)
if deploy_result.stderr:
    print(deploy_result.stderr)
if deploy_result.returncode == 0:
    print("Streamlit app deployed successfully!")
else:
    print(f"Deploy exited with code {deploy_result.returncode}")
