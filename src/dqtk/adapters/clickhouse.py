from typing import Any

import clickhouse_connect

from .base import Adapter, ColumnInfo


class ClickHouseAdapter(Adapter):
    def __init__(
        self,
        host: str,
        port: int = 8123,
        username: str = "default",
        password: str = "",
        client: Any | None = None,
    ):
        self._client = client or clickhouse_connect.get_client(
            host=host, port=port, username=username, password=password
        )

    def row_count(self, table: str) -> int:
        return int(self._client.query(f"select count(*) from {table}").result_rows[0][0])

    def max_value(self, table: str, column: str) -> Any:
        return self._client.query(f"select max({column}) from {table}").result_rows[0][0]

    def null_rate(self, table: str, column: str) -> float:
        row = self._client.query(
            f"select count(*), countIf({column} is null) from {table}"
        ).result_rows[0]
        total, nulls = row
        if total == 0:
            return 0.0
        return nulls / total

    def columns(self, table: str) -> list[ColumnInfo]:
        database, _, bare_table = table.rpartition(".")
        rows = self._client.query(
            "select name, type from system.columns where database = {database:String} "
            "and table = {table:String} order by position",
            parameters={"database": database or "default", "table": bare_table},
        ).result_rows
        return [ColumnInfo(name=r[0], type=r[1]) for r in rows]

    def close(self) -> None:
        self._client.close()
