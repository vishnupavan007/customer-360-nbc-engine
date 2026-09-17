"""Deploy semantic view using Snowpark session."""
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from snowflake.snowpark import Session

session = Session.builder.configs({
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "role": "ACCOUNTADMIN",
    "warehouse": "COMPUTE_WH",
    "database": "CUSTOMER_360",
    "schema": "APP",
}).create()

yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "semantic", "customer_360_semantic.yaml")
with open(yaml_path, "r", encoding="utf-8") as f:
    yaml_content = f.read()

sql = "CREATE OR REPLACE SEMANTIC VIEW CUSTOMER_360.APP.CUSTOMER_360_SEMANTIC_VIEW\n$$\n" + yaml_content + "\n$$"

print("Creating semantic view...")
try:
    result = session.sql(sql).collect()
    print("SUCCESS:", result)
except Exception as e:
    print(f"Error: {e}")

session.close()
