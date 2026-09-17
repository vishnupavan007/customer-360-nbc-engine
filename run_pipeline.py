"""
Customer 360 - SQL Pipeline Runner
Executes all SQL scripts in order against Snowflake using snowflake-connector-python.

Usage:
    pip install snowflake-connector-python python-dotenv
    python run_pipeline.py

Reads connection config from .env file in the same directory.
"""

import getpass
import os
import re
import sys
import time
from dotenv import load_dotenv
import snowflake.connector

# Load .env file from the same directory as this script
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# --- Connection config (loaded from .env) ---
CONN_PARAMS = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT", "sdhndje-sq84485"),
    "user": os.getenv("SNOWFLAKE_USER", "VISHNUPAVAN"),
    "role": os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
}

# --- SQL files in execution order ---
SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql")

SQL_FILES = [
    "00_setup.sql",
    "01_raw_tables.sql",
    "02_synthetic_data.sql",
    "03_clean_dynamic_tables.sql",
    "04_curated_dynamic_tables.sql",
    "05_ai_enrichment.sql",
    "06_semantic_model.sql",
    "07_cortex_agent.sql",
    "08_tasks_and_monitoring.sql",
    "09_validation.sql",
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
    # Resolve password: env var, then interactive prompt
    password = os.getenv("SNOWFLAKE_PASSWORD", "")
    if not password:
        password = getpass.getpass(f"Enter Snowflake password for {CONN_PARAMS['user']}: ")
    if not password:
        print("ERROR: Password is required.")
        sys.exit(1)
    CONN_PARAMS["password"] = password

    # Verify SQL directory exists
    if not os.path.isdir(SQL_DIR):
        print(f"ERROR: SQL directory not found: {SQL_DIR}")
        sys.exit(1)

    print("=" * 70)
    print("Customer 360 - Pipeline Deployment")
    print(f"Account:   {CONN_PARAMS['account']}")
    print(f"User:      {CONN_PARAMS['user']}")
    print(f"Role:      {CONN_PARAMS['role']}")
    print(f"Warehouse: {CONN_PARAMS['warehouse']}")
    print(f"SQL Dir:   {SQL_DIR}")
    print("=" * 70)

    conn = snowflake.connector.connect(**CONN_PARAMS)
    cursor = conn.cursor()

    total_success = 0
    total_errors = 0
    file_results = []

    for sql_file in SQL_FILES:
        filepath = os.path.join(SQL_DIR, sql_file)

        if not os.path.exists(filepath):
            print(f"\n  SKIP: {sql_file} (file not found)")
            file_results.append((sql_file, 0, 0, "SKIPPED"))
            continue

        print(f"\n{'─' * 70}")
        print(f"  Running: {sql_file}")
        print(f"{'─' * 70}")

        start = time.time()
        success, errors = run_file(cursor, filepath)
        elapsed = time.time() - start

        total_success += success
        total_errors += errors
        status = "OK" if errors == 0 else f"ERRORS ({errors})"
        file_results.append((sql_file, success, errors, status))

        print(f"\n  Result: {success} succeeded, {errors} failed ({elapsed:.1f}s)")

    # Summary
    print(f"\n{'=' * 70}")
    print("DEPLOYMENT SUMMARY")
    print(f"{'=' * 70}")
    print(f"{'File':<40} {'OK':>5} {'Err':>5}  Status")
    print(f"{'─' * 60}")
    for name, s, e, status in file_results:
        print(f"{name:<40} {s:>5} {e:>5}  {status}")
    print(f"{'─' * 60}")
    print(f"{'TOTAL':<40} {total_success:>5} {total_errors:>5}")
    print(f"{'=' * 70}")

    if total_errors > 0:
        print(f"\nWARNING: {total_errors} statement(s) failed. Review errors above.")
    else:
        print("\nAll statements executed successfully.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
