from typing import Any

from dqtk.adapters.base import Adapter, ColumnInfo

from .base import Check, CheckResult, Status


class SchemaDriftCheck(Check):
    """Detects column additions, removals, and type changes since the last run.

    `previous_columns` (passed by the caller, loaded from the stored schema
    snapshot of the last run) is compared against the table's current
    schema. With no previous snapshot, the check passes and reports the
    current schema as the new baseline.
    """

    name = "schema_drift"

    def run(
        self,
        adapter: Adapter,
        table: str,
        previous_columns: list[ColumnInfo] | None = None,
        **context: Any,
    ) -> CheckResult:
        current = adapter.columns(table)
        current_by_name = {c.name: c.type for c in current}

        if previous_columns is None:
            return self._result(
                table,
                Status.PASS,
                f"{table} schema snapshot recorded ({len(current)} columns, no prior baseline)",
                columns=current_by_name,
            )

        previous_by_name = {c.name: c.type for c in previous_columns}

        added = sorted(set(current_by_name) - set(previous_by_name))
        removed = sorted(set(previous_by_name) - set(current_by_name))
        type_changed = sorted(
            name
            for name in set(current_by_name) & set(previous_by_name)
            if current_by_name[name] != previous_by_name[name]
        )

        if not added and not removed and not type_changed:
            return self._result(
                table,
                Status.PASS,
                f"{table} schema unchanged ({len(current)} columns)",
                columns=current_by_name,
            )

        parts = []
        if added:
            parts.append(f"added={added}")
        if removed:
            parts.append(f"removed={removed}")
        if type_changed:
            parts.append(f"type_changed={type_changed}")

        status = Status.FAIL if removed or type_changed else Status.WARN
        return self._result(
            table,
            status,
            f"{table} schema drift detected: " + ", ".join(parts),
            added=added,
            removed=removed,
            type_changed=type_changed,
            columns=current_by_name,
        )
