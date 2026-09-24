"""
deploy_daily_pipeline.py
Deploys the daily synthetic data ingestion stored procedure and Task.

Usage:
    python scripts/deploy_daily_pipeline.py            # deploy + start task
    python scripts/deploy_daily_pipeline.py --suspend  # deploy but leave task suspended
    python scripts/deploy_daily_pipeline.py --test     # deploy and run once immediately
    python scripts/deploy_daily_pipeline.py --status   # show task status and last 5 runs
    python scripts/deploy_daily_pipeline.py --pause    # suspend the task
    python scripts/deploy_daily_pipeline.py --resume   # resume a suspended task
"""

import argparse
import os
import sys

from dotenv import load_dotenv
import snowflake.connector

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

CONN_PARAMS = {
    "account":   os.getenv("SNOWFLAKE_ACCOUNT", ""),
    "user":      os.getenv("SNOWFLAKE_USER", ""),
    "password":  os.getenv("SNOWFLAKE_PASSWORD", ""),
    "role":      os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    "database":  "CUSTOMER_360",
    "schema":    "RAW",
}

SQL_FILE  = os.path.join(PROJECT_ROOT, "ops", "10_daily_raw_pipeline.sql")
TASK_FQN  = "CUSTOMER_360.RAW.TASK_DAILY_RAW_INGEST"
PROC_FQN  = "CUSTOMER_360.RAW.SP_DAILY_SYNTHETIC_DATA"


def connect():
    print(f"Connecting  account={CONN_PARAMS['account']}  user={CONN_PARAMS['user']}")
    return snowflake.connector.connect(**CONN_PARAMS)


def run_sql(cur, sql, label=""):
    """Execute a single SQL statement."""
    try:
        cur.execute(sql)
        print(f"  OK  rows={cur.rowcount}  | {label or sql[:70]}")
    except Exception as e:
        print(f"  ERROR [{label}]: {e}", file=sys.stderr)
        raise


def read_proc_sql():
    """Extract the stored procedure CREATE statement from the SQL file.
    Returns it as a single string (contains ; inside $$ body).
    """
    raw = open(SQL_FILE, encoding='utf-8').read()
    # Find the CREATE OR REPLACE PROCEDURE block
    start = raw.index('CREATE OR REPLACE PROCEDURE')
    # The proc ends at the closing $$ followed by ;
    end = raw.index('$$;', start) + 3  # include the $$;
    return raw[start:end]


def deploy(suspend=False):
    conn = connect()
    cur = conn.cursor()
    try:
        print("\nSetting context...")
        run_sql(cur, "USE DATABASE CUSTOMER_360", "USE DATABASE")
        run_sql(cur, "USE SCHEMA RAW", "USE SCHEMA")
        run_sql(cur, "USE WAREHOUSE COMPUTE_WH", "USE WAREHOUSE")

        print("\nCreating stored procedure...")
        proc_sql = read_proc_sql()
        run_sql(cur, proc_sql, "CREATE OR REPLACE PROCEDURE SP_DAILY_SYNTHETIC_DATA")

        print("\nCreating task...")
        task_sql = (
            "CREATE OR REPLACE TASK CUSTOMER_360.RAW.TASK_DAILY_RAW_INGEST\n"
            "    WAREHOUSE = COMPUTE_WH\n"
            "    SCHEDULE  = 'USING CRON 0 */6 * * * UTC'\n"
            "    COMMENT   = 'Daily synthetic data ingestion for Customer 360 pipeline'\n"
            f"AS\n    CALL {PROC_FQN}(20)"
        )
        run_sql(cur, task_sql, "CREATE OR REPLACE TASK TASK_DAILY_RAW_INGEST")

        if not suspend:
            run_sql(cur, f"ALTER TASK {TASK_FQN} RESUME", "RESUME task")
            print(f"\nTask {TASK_FQN} is ACTIVE.")
            print("  Schedule : every 6 hours UTC (CRON 0 */6 * * *)")
            print("  Batch    : 20 new customers + proportional records per run")
        else:
            print(f"\nTask {TASK_FQN} created but left SUSPENDED.")
            print(f"  Resume with:  ALTER TASK {TASK_FQN} RESUME;")
    finally:
        cur.close()
        conn.close()


def test_run():
    """Deploy then immediately call the procedure to verify it works."""
    deploy(suspend=False)

    conn = connect()
    cur = conn.cursor()
    try:
        print("\nRunning test batch (BATCH_SIZE=5)...")
        cur.execute(f"CALL {PROC_FQN}(5)")
        result = cur.fetchone()
        print(f"\nResult:\n  {result[0]}")
        print("\nTest passed. Task is active and will run at midnight UTC.")
    finally:
        cur.close()
        conn.close()


def show_status():
    conn = connect()
    cur = conn.cursor()
    try:
        print("\nTask status:")
        cur.execute(f"SHOW TASKS LIKE 'TASK_DAILY_RAW_INGEST' IN SCHEMA CUSTOMER_360.RAW")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        for row in rows:
            r = dict(zip(cols, row))
            print(f"  Name     : {r.get('name')}")
            print(f"  State    : {r.get('state')}")
            print(f"  Schedule : {r.get('schedule')}")
            print(f"  Warehouse: {r.get('warehouse')}")
            print(f"  Created  : {r.get('created_on')}")

        print("\nLast 10 task runs:")
        cur.execute("""
            SELECT NAME, STATE, SCHEDULED_TIME, COMPLETED_TIME,
                   DATEDIFF('second', SCHEDULED_TIME, COMPLETED_TIME) AS DUR_SEC,
                   ERROR_CODE, ERROR_MESSAGE
            FROM TABLE(SNOWFLAKE.INFORMATION_SCHEMA.TASK_HISTORY(
                TASK_NAME => 'TASK_DAILY_RAW_INGEST',
                SCHEDULED_TIME_RANGE_START => DATEADD('day', -30, CURRENT_TIMESTAMP()),
                RESULT_LIMIT => 10
            ))
            WHERE DATABASE_NAME = 'CUSTOMER_360' AND SCHEMA_NAME = 'RAW'
              AND SCHEDULED_TIME <= CURRENT_TIMESTAMP()
            ORDER BY SCHEDULED_TIME DESC
        """)
        runs = cur.fetchall()
        if not runs:
            print("  No completed runs yet.")
        else:
            for run in runs:
                state, sched, comp, dur, ec, em = run[1], run[2], run[3], run[4], run[5], run[6]
                icon = "OK" if state == 'SUCCEEDED' else "FAIL"
                print(f"  [{icon}] {state:<12} at {sched}  ({dur}s)  err={ec or '-'}")
                if em:
                    print(f"          {em}")

        print("\nCurrent RAW table row counts:")
        cur.execute("""
            SELECT 'RAW_CUSTOMERS'       AS T, COUNT(*) AS CNT FROM CUSTOMER_360.RAW.RAW_CUSTOMERS
            UNION ALL SELECT 'RAW_POLICIES',        COUNT(*) FROM CUSTOMER_360.RAW.RAW_POLICIES
            UNION ALL SELECT 'RAW_CLAIMS',           COUNT(*) FROM CUSTOMER_360.RAW.RAW_CLAIMS
            UNION ALL SELECT 'RAW_LOANS',            COUNT(*) FROM CUSTOMER_360.RAW.RAW_LOANS
            UNION ALL SELECT 'RAW_INTERACTIONS',     COUNT(*) FROM CUSTOMER_360.RAW.RAW_INTERACTIONS
            UNION ALL SELECT 'RAW_CALL_TRANSCRIPTS', COUNT(*) FROM CUSTOMER_360.RAW.RAW_CALL_TRANSCRIPTS
            ORDER BY 1
        """)
        for row in cur.fetchall():
            print(f"  {row[0]:<25} {row[1]:>6,} rows")
    finally:
        cur.close()
        conn.close()


def pause_task():
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute(f"ALTER TASK {TASK_FQN} SUSPEND")
        print(f"Task {TASK_FQN} suspended.")
    finally:
        cur.close()
        conn.close()


def resume_task():
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute(f"ALTER TASK {TASK_FQN} RESUME")
        print(f"Task {TASK_FQN} resumed. Next run at midnight UTC.")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy/manage daily raw data pipeline")
    parser.add_argument("--suspend", action="store_true", help="Deploy without resuming the task")
    parser.add_argument("--test",    action="store_true", help="Deploy and run a test batch of 5 records")
    parser.add_argument("--status",  action="store_true", help="Show task status and recent run history")
    parser.add_argument("--pause",   action="store_true", help="Suspend the running task")
    parser.add_argument("--resume",  action="store_true", help="Resume a suspended task")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.test:
        test_run()
    elif args.pause:
        pause_task()
    elif args.resume:
        resume_task()
    else:
        deploy(suspend=args.suspend)
