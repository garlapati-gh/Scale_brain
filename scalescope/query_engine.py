from __future__ import annotations

import os
import re
import sqlite3

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from database import DB_LOCK


SCHEMA = """
projects(id, name, client, domain, status, priority, start_date, due_date, budget_usd)
workers(id, name, team, location, hourly_rate_usd)
tasks(id, project_id, worker_id, title, status, priority, created_at, due_date,
      completed_at, estimated_hours, actual_hours, quality_score)
reviews(id, task_id, reviewer_id, score, notes, reviewed_at)
""".strip()
ALLOWED_TABLES = {"projects", "workers", "tasks", "reviews"}
MAX_ROWS = 250


class QueryError(ValueError):
    """A user-facing query or SQL safety error."""


def _api_key() -> str | None:
    load_dotenv()
    return os.getenv("OPENROUTER_API_KEY")


def is_configured() -> bool:
    return bool(_api_key())


def generate_sql(question: str) -> str:
    api_key = _api_key()
    if not api_key:
        raise QueryError("Set OPENROUTER_API_KEY to enable natural-language questions.")
    if not question.strip():
        raise QueryError("Enter a question about the operational data.")

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={"HTTP-Referer": "http://localhost:8501", "X-Title": "ScaleScope"},
    )
    response = client.chat.completions.create(
        model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Translate the user's analytics question into one SQLite SELECT query. "
                    "Use only the listed tables and columns. Return SQL only, without markdown. "
                    "Never write, update, delete, attach, or inspect schema. Prefer readable "
                    "aliases, use ISO date strings for date comparisons, and cap results at "
                    f"{MAX_ROWS} rows. Schema:\n{SCHEMA}"
                ),
            },
            {"role": "user", "content": question.strip()},
        ],
    )
    content = response.choices[0].message.content or ""
    sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
    sql = re.sub(r"^SQL\s*:\s*", "", sql, flags=re.IGNORECASE).strip()
    return sql


def _authorize(action: int, first: str | None, second: str | None, database: str | None, trigger: str | None) -> int:
    if action == sqlite3.SQLITE_READ:
        return sqlite3.SQLITE_OK if first in ALLOWED_TABLES else sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION:
        function_name = (second or "").lower()
        return sqlite3.SQLITE_DENY if function_name in {"load_extension", "writefile", "readfile"} else sqlite3.SQLITE_OK
    if action in {sqlite3.SQLITE_SELECT, getattr(sqlite3, "SQLITE_RECURSIVE", -1)}:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def execute_readonly(sql: str, connection: sqlite3.Connection) -> pd.DataFrame:
    normalized = sql.strip().rstrip(";").strip()
    if not re.match(r"^(SELECT|WITH)\b", normalized, flags=re.IGNORECASE):
        raise QueryError("Only a single read-only SELECT query is allowed.")
    if ";" in normalized:
        raise QueryError("Only one SQL statement is allowed.")

    with DB_LOCK:
        connection.set_authorizer(_authorize)
        try:
            cursor = connection.execute(normalized)
            if cursor.description is None:
                raise QueryError("The query did not return a result set.")
            rows = cursor.fetchmany(MAX_ROWS)
            return pd.DataFrame.from_records(rows, columns=[column[0] for column in cursor.description])
        except sqlite3.DatabaseError as error:
            raise QueryError(f"Could not run that query: {error}") from error
        finally:
            connection.set_authorizer(None)


def ask(question: str, connection: sqlite3.Connection) -> tuple[str, pd.DataFrame]:
    sql = generate_sql(question)
    return sql, execute_readonly(sql, connection)