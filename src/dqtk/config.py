from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from dqtk.adapters.base import Adapter
from dqtk.adapters.clickhouse import ClickHouseAdapter
from dqtk.adapters.postgres import PostgresAdapter
from dqtk.checks import REGISTRY as CHECK_REGISTRY
from dqtk.checks.base import Check
from dqtk.notifiers import REGISTRY as NOTIFIER_REGISTRY
from dqtk.notifiers.base import Notifier

ADAPTER_REGISTRY = {
    "postgres": PostgresAdapter,
    "clickhouse": ClickHouseAdapter,
}


@dataclass
class TableConfig:
    name: str
    adapter_name: str
    checks: list[Check]


@dataclass
class DqtkConfig:
    storage_dsn: str
    adapters: dict[str, Adapter]
    notifiers: list[Notifier]
    tables: list[TableConfig]

    def close(self) -> None:
        for adapter in self.adapters.values():
            adapter.close()


def _build_adapter(spec: dict[str, Any]) -> Adapter:
    spec = dict(spec)
    adapter_type = spec.pop("type")
    try:
        cls = ADAPTER_REGISTRY[adapter_type]
    except KeyError:
        raise ValueError(f"unknown adapter type: {adapter_type}") from None
    return cls(**spec)


def _build_check(spec: dict[str, Any]) -> Check:
    spec = dict(spec)
    check_type = spec.pop("type")
    try:
        cls = CHECK_REGISTRY[check_type]
    except KeyError:
        raise ValueError(f"unknown check type: {check_type}") from None
    return cls(**spec)


def _build_notifier(spec: dict[str, Any]) -> Notifier:
    spec = dict(spec)
    notifier_type = spec.pop("type")
    try:
        cls = NOTIFIER_REGISTRY[notifier_type]
    except KeyError:
        raise ValueError(f"unknown notifier type: {notifier_type}") from None
    return cls(**spec)


def load_config(path: str | Path) -> DqtkConfig:
    raw = yaml.safe_load(Path(path).read_text())

    adapters = {name: _build_adapter(spec) for name, spec in raw["adapters"].items()}
    notifiers = [_build_notifier(spec) for spec in raw.get("notifiers", [])]
    tables = [
        TableConfig(
            name=table["name"],
            adapter_name=table["adapter"],
            checks=[_build_check(c) for c in table["checks"]],
        )
        for table in raw["tables"]
    ]

    return DqtkConfig(
        storage_dsn=raw["storage"]["dsn"],
        adapters=adapters,
        notifiers=notifiers,
        tables=tables,
    )
