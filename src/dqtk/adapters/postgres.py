from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .base import Adapter, ColumnInfo


class PostgresAdapter(Adapter):
    def __init__(self, dsn: str, engine: Engine | None = None):
        self.dsn = dsn
        self._engine = engine or create_engine(dsn)

    def row_count(self, table: str) -> int:
        with self._engine.connect() as conn:
            return conn.execute(text(f"select count(*) from {table}")).scalar_one()

    def max_value(self, table: str, column: str) -> Any:
        with self._engine.connect() as conn:
            return conn.execute(text(f"select max({column}) from {table}")).scalar_one()

    def null_rate(self, table: str, column: str) -> float:
        with self._engine.connect() as conn:
            total, nulls = conn.execute(
                text(
                    f"select count(*), "
                    f"count(*) - count({column}) "
                    f"from {table}"
                )
            ).one()
        if total == 0:
            return 0.0
        return nulls / total

    def columns(self, table: str) -> list[ColumnInfo]:
        schema, _, bare_table = table.rpartition(".")
        schema = schema or "public"
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "select column_name, data_type "
                    "from information_schema.columns "
                    "where table_schema = :schema and table_name = :table "
                    "order by ordinal_position"
                ),
                {"schema": schema, "table": bare_table},
            ).all()
        return [ColumnInfo(name=r[0], type=r[1]) for r in rows]

    def close(self) -> None:
        self._engine.dispose()
