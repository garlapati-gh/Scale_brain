from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from database import create_database
from query_engine import (
    MAX_ROWS,
    QueryError,
    ask,
    execute_readonly,
    generate_sql,
    is_configured,
)


class TestQueryEngine:
    """Test suite for the ScaleScope text-to-SQL engine and read-only execution guardrails."""

    @pytest.fixture
    def db_conn(self):
        """Provide a clean in-memory database connection for each test."""
        conn = create_database()
        yield conn
        conn.close()

    def test_is_configured(self, monkeypatch):
        """Verify configuration detection based on environment variable."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-12345")
        assert is_configured() is True

        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        # Prevent dotenv from reloading real file during test
        with patch("query_engine.load_dotenv"):
            assert is_configured() is False

    def test_execute_readonly_valid_select(self, db_conn):
        """Verify standard SELECT queries execute cleanly and return DataFrames."""
        df = execute_readonly("SELECT id, name FROM workers LIMIT 3", db_conn)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["id", "name"]

    def test_execute_readonly_cte_query(self, db_conn):
        """Verify CTE queries with WITH clauses execute properly."""
        sql = """
        WITH high_perf_workers AS (
            SELECT worker_id, AVG(quality_score) as avg_score
            FROM tasks
            WHERE quality_score IS NOT NULL
            GROUP BY worker_id
            HAVING avg_score >= 4.0
        )
        SELECT * FROM high_perf_workers LIMIT 5
        """
        df = execute_readonly(sql, db_conn)
        assert isinstance(df, pd.DataFrame)
        assert len(df) <= 5

    def test_execute_readonly_blocks_dml(self, db_conn):
        """Verify DML statements (INSERT, UPDATE, DELETE) are rejected."""
        insert_sql = (
            "INSERT INTO workers (id, name, team, location, hourly_rate_usd) "
            "VALUES (999, 'Test', 'T', 'L', 50)"
        )
        with pytest.raises(QueryError, match="Only a single read-only SELECT query is allowed"):
            execute_readonly(insert_sql, db_conn)

        with pytest.raises(QueryError, match="Only a single read-only SELECT query is allowed"):
            execute_readonly("UPDATE workers SET name = 'Attacker' WHERE id = 1", db_conn)

        with pytest.raises(QueryError, match="Only a single read-only SELECT query is allowed"):
            execute_readonly("DELETE FROM tasks", db_conn)

    def test_execute_readonly_blocks_ddl(self, db_conn):
        """Verify DDL statements (DROP, CREATE, ALTER) are rejected."""
        with pytest.raises(QueryError, match="Only a single read-only SELECT query is allowed"):
            execute_readonly("DROP TABLE tasks", db_conn)

        with pytest.raises(QueryError, match="Only a single read-only SELECT query is allowed"):
            execute_readonly("CREATE TABLE evil (id INT)", db_conn)

    def test_execute_readonly_blocks_multiple_statements(self, db_conn):
        """Verify stacked/multiple SQL statements separated by semicolons are rejected."""
        with pytest.raises(QueryError, match="Only one SQL statement is allowed"):
            execute_readonly("SELECT 1 FROM workers; DROP TABLE tasks;", db_conn)

    def test_execute_readonly_enforces_allowed_tables(self, db_conn):
        """Verify the SQLite authorizer blocks queries to unauthorized or internal schema tables."""
        # Querying sqlite_master is blocked by authorizer
        with pytest.raises(QueryError, match="Could not run that query"):
            execute_readonly("SELECT * FROM sqlite_master", db_conn)

    def test_execute_readonly_caps_max_rows(self, db_conn):
        """Verify result sets never exceed MAX_ROWS limit."""
        df = execute_readonly("SELECT * FROM tasks", db_conn)
        assert len(df) <= MAX_ROWS
        assert len(df) == 250

    def test_generate_sql_missing_api_key(self, monkeypatch):
        """Verify generate_sql raises QueryError when API key is missing."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        with patch("query_engine.load_dotenv"):
            with pytest.raises(QueryError, match="Set OPENROUTER_API_KEY to enable"):
                generate_sql("Which project has the highest budget?")

    def test_generate_sql_empty_question(self, monkeypatch):
        """Verify generate_sql raises QueryError on blank input."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-mock-key")
        with pytest.raises(QueryError, match="Enter a question"):
            generate_sql("   ")

    def test_generate_sql_cleans_markdown(self, monkeypatch):
        """Verify markdown wrappers (```sql ... ```) and 'SQL:' prefixes are stripped."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-mock-key")

        mock_choice = MagicMock()
        mock_choice.message.content = "```sql\nSELECT COUNT(*) FROM tasks;\n```"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("query_engine.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_cls.return_value = mock_client

            clean_sql = generate_sql("How many tasks are there?")
            assert clean_sql == "SELECT COUNT(*) FROM tasks;"

    def test_ask_integration_flow(self, monkeypatch, db_conn):
        """Verify the ask() function pipeline from prompt to DataFrame."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-mock-key")

        mock_choice = MagicMock()
        mock_choice.message.content = "SELECT COUNT(*) AS total_workers FROM workers"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("query_engine.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_cls.return_value = mock_client

            sql, df = ask("How many workers?", db_conn)
            assert sql == "SELECT COUNT(*) AS total_workers FROM workers"
            assert isinstance(df, pd.DataFrame)
            assert df.loc[0, "total_workers"] == 18

