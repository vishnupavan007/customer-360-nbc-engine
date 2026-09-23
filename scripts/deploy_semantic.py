"""Deploy semantic view using snowflake-connector-python."""
import os
from dotenv import load_dotenv
import snowflake.connector

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    role="ACCOUNTADMIN",
    warehouse="COMPUTE_WH",
    database="CUSTOMER_360",
    schema="APP",
)
cur = conn.cursor()

yaml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "serving", "semantic_model", "customer_360_semantic.yaml")
with open(yaml_path, "r", encoding="utf-8") as f:
    yaml_content = f.read()

sql = "CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML('CUSTOMER_360.APP', $$\n" + yaml_content + "\n$$)"

print("Creating semantic view...")
try:
    cur.execute(sql)
    result = cur.fetchone()
    print("SUCCESS:", result)
except Exception as e:
    print(f"Error: {e}")

cur.close()
conn.close()
