"""Database connection and schema management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from etl.config import AppConfig, PROJECT_ROOT

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections, schema initialization, and queries."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.engine: Engine = create_engine(
            config.database.connection_string,
            echo=False,
            pool_pre_ping=True,
        )

    def initialize_schema(self) -> None:
        """Execute SQL schema, index, and view scripts."""
        sql_dirs = ["schema", "indexes", "views"]
        for sql_dir in sql_dirs:
            dir_path = PROJECT_ROOT / "sql" / sql_dir
            if not dir_path.exists():
                continue
            for sql_file in sorted(dir_path.glob("*.sql")):
                logger.info("Executing %s", sql_file.name)
                self._execute_sql_file(sql_file)

    def _execute_sql_file(self, filepath: Path) -> None:
        with open(filepath) as f:
            sql_content = f.read()
        statements = [s.strip() for s in sql_content.split(";") if s.strip()]
        with self.engine.begin() as conn:
            for statement in statements:
                if statement:
                    conn.execute(text(statement))

    def execute_query(self, query: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
        """Execute a SQL query and return results as DataFrame."""
        with self.engine.connect() as conn:
            return pd.read_sql(text(query), conn, params=params or {})

    def insert_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = "append",
        index: bool = False,
    ) -> int:
        """Insert DataFrame into database table."""
        rows = df.to_sql(table_name, self.engine, if_exists=if_exists, index=index)
        return rows if rows else len(df)

    def bulk_insert(self, records: list[dict[str, Any]], table_name: str) -> int:
        """Bulk insert records using executemany."""
        if not records:
            return 0
        columns = records[0].keys()
        placeholders = ", ".join(f":{col}" for col in columns)
        col_names = ", ".join(columns)
        query = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
        with self.engine.begin() as conn:
            conn.execute(text(query), records)
        return len(records)

    def truncate_table(self, table_name: str) -> None:
        """Clear all records from a table."""
        with self.engine.begin() as conn:
            conn.execute(text(f"DELETE FROM {table_name}"))

    def get_table_count(self, table_name: str) -> int:
        """Return row count for a table."""
        result = self.execute_query(f"SELECT COUNT(*) as cnt FROM {table_name}")
        return int(result["cnt"].iloc[0])

    def table_exists(self, table_name: str) -> bool:
        """Check if table exists in database."""
        if self.config.database.db_type == "sqlite":
            query = "SELECT name FROM sqlite_master WHERE type='table' AND name=:name"
        else:
            query = (
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name = :name"
            )
        result = self.execute_query(query, {"name": table_name})
        return len(result) > 0

    def log_pipeline_run(
        self,
        run_date: str,
        pipeline_name: str,
        status: str,
        records_processed: int = 0,
        exceptions_found: int = 0,
        error_message: str | None = None,
    ) -> None:
        """Log pipeline execution to pipeline_runs table."""
        query = """
            INSERT INTO pipeline_runs
            (run_date, pipeline_name, status, records_processed,
             exceptions_found, completed_at, error_message)
            VALUES (:run_date, :pipeline_name, :status, :records_processed,
                    :exceptions_found, CURRENT_TIMESTAMP, :error_message)
        """
        with self.engine.begin() as conn:
            conn.execute(
                text(query),
                {
                    "run_date": run_date,
                    "pipeline_name": pipeline_name,
                    "status": status,
                    "records_processed": records_processed,
                    "exceptions_found": exceptions_found,
                    "error_message": error_message,
                },
            )
