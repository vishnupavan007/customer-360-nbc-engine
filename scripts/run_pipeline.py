"""
Customer 360 - SQL Pipeline Runner
Executes all SQL scripts in order against Snowflake using snowflake-connector-python.

Usage:
    pip install snowflake-connector-python python-dotenv
    python run_pipeline.py

Reads connection config from .env file in the project root (parent of scripts/).
"""

import getpass
import os
import re
import sys
import time
from dotenv import load_dotenv
import snowflake.connector

# Load .env from project root (parent of scripts/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# --- Connection config (loaded from .env) ---
CONN_PARAMS = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT", ""),
    "user": os.getenv("SNOWFLAKE_USER", ""),
    "role": os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
}

# --- SQL files in execution order (relative to project root) ---
# Each entry is (relative_path_from_root, description)
SQL_FILES = [
    ("infrastructure/00_setup.sql",                    "Infrastructure: schemas and warehouse"),
    ("pipeline/schema/01_raw_tables.sql",               "Pipeline: raw table DDL"),
    ("pipeline/data/02_synthetic_data.sql",             "Pipeline: synthetic data generation"),
    ("pipeline/clean/03_clean_dynamic_tables.sql",      "Pipeline: CLEAN dynamic tables"),
    ("pipeline/curated/04_curated_dynamic_tables.sql",  "Pipeline: CURATED unified view"),
    ("pipeline/ai/05_ai_enrichment.sql",                "Pipeline: AI enrichment + Cortex Search"),
    ("serving/semantic_model/06_semantic_model.sql",    "Serving: semantic view creation"),
    ("serving/agent/07_cortex_agent.sql",               "Serving: Cortex Agent documentation"),
    ("ops/08_tasks_and_monitoring.sql",                 "Ops: scheduled quality monitoring tasks"),
    ("ops/09_validation.sql",                           "Ops: end-to-end validation queries"),
]


def split_statements(sql_text: str) -> list[str]:
    """Split a SQL file into individual statements on semicolons.
    Correctly handles:
    - Single-line comments (--)
    - Single-quoted strings (won't split on ; inside strings)
    - BEGIN...END scripting blocks (won't split on ; inside blocks)
    """
    statements = []
    current = []
    in_string = False
    block_depth = 0

    for line in sql_text.split("\n"):
        stripped = line.strip()

        # Always preserve the line with a newline for proper formatting
        if stripped.startswith("--"):
            # Comment-only line: add to current statement buffer but don't process for ;
            current.append(line + "\n")
            continue

        i = 0
        line_len = len(line)
        while i < line_len:
            ch = line[i]

            # Check for single-line comment start
            if ch == '-' and i + 1 < line_len and line[i + 1] == '-' and not in_string:
                # Rest of line is a comment, append it and move to next line
                current.append(line[i:])
                break

            # Track single-quoted strings (handle escaped quotes '')
            if ch == "'":
                if in_string:
                    # Check for escaped quote ''
                    if i + 1 < line_len and line[i + 1] == "'":
                        current.append("''")
                        i += 2
                        continue
                    else:
                        in_string = False
                else:
                    in_string = True
                current.append(ch)
                i += 1
                continue

            if in_string:
                current.append(ch)
                i += 1
                continue

            # Track BEGIN/END blocks for scripting (CREATE TASK ... AS BEGIN ... END)
            upper_rest = line[i:].upper()
            if re.match(r'^BEGIN\b', upper_rest):
                block_depth += 1
                current.append(ch)
                i += 1
                continue

            if re.match(r'^END\b', upper_rest):
                if block_depth > 0:
                    block_depth -= 1
                current.append(ch)
                i += 1
                continue

            # Semicolon outside string and outside block = statement delimiter
            if ch == ';' and block_depth == 0:
                stmt_text = "".join(current).strip()
                # Only keep statements that have actual SQL (not just comments)
                if stmt_text:
                    # Check it's not entirely comments
                    non_comment_lines = [
                        l for l in stmt_text.split("\n")
                        if l.strip() and not l.strip().startswith("--")
                    ]
                    if non_comment_lines:
                        statements.append(stmt_text)
                current = []
                i += 1
                continue

            current.append(ch)
            i += 1

        # End of line - add newline
        current.append("\n")

    # Catch trailing statement without semicolon
    remaining = "".join(current).strip()
    if remaining:
        non_comment_lines = [
            l for l in remaining.split("\n")
            if l.strip() and not l.strip().startswith("--")
        ]
        if non_comment_lines:
            statements.append(remaining)

    return statements


def run_file(cursor, filepath: str) -> tuple[int, int]:
    """Execute all statements in a SQL file. Returns (success_count, error_count)."""
    with open(filepath, "r", encoding="utf-8") as f:
        sql_text = f.read()

    statements = split_statements(sql_text)
    success = 0
    errors = 0

    for idx, stmt in enumerate(statements, 1):
        # Show first non-comment line for context
        display_lines = [
            l.strip() for l in stmt.split("\n")
            if l.strip() and not l.strip().startswith("--")
        ]
        first_line = (display_lines[0] if display_lines else stmt.strip().split("\n")[0])[:120]
        print(f"    [{idx}/{len(statements)}] {first_line}")

        try:
            cursor.execute(stmt)
            result = cursor.fetchone()
            if result:
                print(f"             -> {result[0] if len(result) == 1 else result}")
            success += 1
        except snowflake.connector.errors.ProgrammingError as e:
            print(f"             !! ERROR: {e.msg}")
            errors += 1

    return success, errors


def main():
    # Validate required connection params are set
    if not CONN_PARAMS.get("account"):
        print("ERROR: SNOWFLAKE_ACCOUNT is not set. Add it to your .env file.")
        sys.exit(1)
    if not CONN_PARAMS.get("user"):
        print("ERROR: SNOWFLAKE_USER is not set. Add it to your .env file.")
        sys.exit(1)

    # Resolve password: env var, then interactive prompt
    password = os.getenv("SNOWFLAKE_PASSWORD", "")
    if not password:
        password = getpass.getpass(f"Enter Snowflake password for {CONN_PARAMS['user']}: ")
    if not password:
        print("ERROR: Password is required.")
        sys.exit(1)
    CONN_PARAMS["password"] = password

    # Verify SQL directory exists
    if not os.path.isdir(PROJECT_ROOT):
        print(f"ERROR: Project root not found: {PROJECT_ROOT}")
        sys.exit(1)

    print("=" * 70)
    print("Customer 360 - Pipeline Deployment")
    print(f"Account:   {CONN_PARAMS['account']}")
    print(f"User:      {CONN_PARAMS['user']}")
    print(f"Role:      {CONN_PARAMS['role']}")
    print(f"Warehouse: {CONN_PARAMS['warehouse']}")
    print(f"Root:      {PROJECT_ROOT}")
    print("=" * 70)

    conn = snowflake.connector.connect(**CONN_PARAMS)
    cursor = conn.cursor()

    total_success = 0
    total_errors = 0
    file_results = []

    for rel_path, description in SQL_FILES:
        filepath = os.path.join(PROJECT_ROOT, rel_path)
        sql_file = os.path.basename(rel_path)

        if not os.path.exists(filepath):
            print(f"\n  SKIP: {rel_path} (file not found)")
            file_results.append((rel_path, 0, 0, "SKIPPED"))
            continue

        print(f"\n{'─' * 70}")
        print(f"  Running: {rel_path}")
        print(f"  ({description})")
        print(f"{'─' * 70}")

        start = time.time()
        success, errors = run_file(cursor, filepath)
        elapsed = time.time() - start

        total_success += success
        total_errors += errors
        status = "OK" if errors == 0 else f"ERRORS ({errors})"
        file_results.append((rel_path, success, errors, status))

        print(f"\n  Result: {success} succeeded, {errors} failed ({elapsed:.1f}s)")

    # Summary
    print(f"\n{'=' * 70}")
    print("DEPLOYMENT SUMMARY")
    print(f"{'=' * 70}")
    print(f"{'File':<50} {'OK':>5} {'Err':>5}  Status")
    print(f"{'─' * 70}")
    for name, s, e, status in file_results:
        short = name.split('/')[-1]
        print(f"{short:<50} {s:>5} {e:>5}  {status}")
    print(f"{'─' * 70}")
    print(f"{'TOTAL':<50} {total_success:>5} {total_errors:>5}")
    print(f"{'=' * 70}")

    if total_errors > 0:
        print(f"\nWARNING: {total_errors} statement(s) failed. Review errors above.")
    else:
        print("\nAll statements executed successfully.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
