import sqlite3
import pandas as pd
import pytest

from database import create_database, read_frame


class TestDatabase:
    """Test suite for the ScaleScope SQLite database creation and data access layer."""

    @pytest.fixture
    def db_conn(self):
        """Provide a clean in-memory database connection for each test."""
        conn = create_database()
        yield conn
        conn.close()

    def test_create_database_connection(self, db_conn):
        """Verify the database connection is initialized and foreign keys are enabled."""
        assert isinstance(db_conn, sqlite3.Connection)
        cursor = db_conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        fk_status = cursor.fetchone()[0]
        assert fk_status == 1, "Foreign key constraints must be enabled"

    def test_database_tables_exist(self, db_conn):
        """Ensure all required relational tables are created."""
        expected_tables = {"projects", "workers", "tasks", "reviews"}
        cursor = db_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

    def test_database_seeded_row_counts(self, db_conn):
        """Ensure synthetic operational dataset is seeded with realistic volumes."""
        df_projects = read_frame(db_conn, "SELECT COUNT(*) AS count FROM projects")
        assert df_projects.loc[0, "count"] == 12

        df_workers = read_frame(db_conn, "SELECT COUNT(*) AS count FROM workers")
        assert df_workers.loc[0, "count"] == 18

        df_tasks = read_frame(db_conn, "SELECT COUNT(*) AS count FROM tasks")
        assert df_tasks.loc[0, "count"] == 700

        df_reviews = read_frame(db_conn, "SELECT COUNT(*) AS count FROM reviews")
        assert df_reviews.loc[0, "count"] > 0

    def test_read_frame_returns_dataframe(self, db_conn):
        """Verify read_frame returns a well-formed pandas DataFrame."""
        df = read_frame(db_conn, "SELECT id, name, team FROM workers LIMIT 5")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert list(df.columns) == ["id", "name", "team"]

    def test_data_integrity(self, db_conn):
        """Verify business logic constraints on seeded data."""
        # Quality score bounds
        df_quality = read_frame(
            db_conn,
            "SELECT MIN(quality_score) AS min_q, MAX(quality_score) AS max_q "
            "FROM tasks WHERE quality_score IS NOT NULL",
        )
        assert df_quality.loc[0, "min_q"] >= 1.0
        assert df_quality.loc[0, "max_q"] <= 5.0

        # Valid task statuses
        valid_statuses = {"completed", "in_progress", "queued", "blocked"}
        df_statuses = read_frame(db_conn, "SELECT DISTINCT status FROM tasks")
        found_statuses = set(df_statuses["status"])
        assert found_statuses.issubset(valid_statuses)

        # Worker hourly rates are positive
        df_rates = read_frame(db_conn, "SELECT MIN(hourly_rate_usd) AS min_rate FROM workers")
        assert df_rates.loc[0, "min_rate"] > 0

    def test_database_deterministic_seeding(self):
        """Verify dataset generator produces identical data across calls due to fixed seed."""
        conn1 = create_database()
        conn2 = create_database()

        df1 = read_frame(conn1, "SELECT id, name, budget_usd FROM projects ORDER BY id")
        df2 = read_frame(conn2, "SELECT id, name, budget_usd FROM projects ORDER BY id")

        conn1.close()
        conn2.close()

        pd.testing.assert_frame_equal(df1, df2)

    def test_foreign_key_enforcement(self, db_conn):
        """Verify foreign key constraint blocks orphaned task insertions."""
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """
                INSERT INTO tasks (
                    id, project_id, worker_id, title, status, priority,
                    created_at, due_date, estimated_hours
                ) VALUES (9999, 999999, 999999, 'Invalid Task', 'queued', 'low',
                          '2026-01-01', '2026-01-05', 2.0)
                """
            )

