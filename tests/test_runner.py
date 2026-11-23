from dqtk.checks import NullRateCheck, RowCountCheck
from dqtk.checks.base import Status
from dqtk.config import DqtkConfig, TableConfig
from dqtk.runner import run_table
from dqtk.storage.run_history import RunHistory

from .conftest import FakeAdapter


def test_run_table_records_results_and_builds_baseline(tmp_path):
    history = RunHistory(f"sqlite:///{tmp_path}/test.db")
    adapter = FakeAdapter(row_counts={"orders": 1000}, null_rates={("orders", "email"): 0.0})
    config = DqtkConfig(storage_dsn="unused", adapters={"main": adapter}, notifiers=[], tables=[])
    table_config = TableConfig(
        name="orders",
        adapter_name="main",
        checks=[RowCountCheck(max_pct_change=0.2, min_history=1), NullRateCheck("email", 0.01)],
    )

    results = run_table(history, config, table_config)

    assert len(results) == 2
    assert all(r.status == Status.PASS for r in results)
    assert history.row_count_history("orders") == [1000]  # this run is now the first history point


def test_run_table_isolates_check_exceptions(tmp_path):
    history = RunHistory(f"sqlite:///{tmp_path}/test.db")
    adapter = FakeAdapter()  # row_counts missing -> KeyError inside the check
    config = DqtkConfig(storage_dsn="unused", adapters={"main": adapter}, notifiers=[], tables=[])
    table_config = TableConfig(name="orders", adapter_name="main", checks=[RowCountCheck()])

    results = run_table(history, config, table_config)

    assert results[0].status == Status.ERROR
    assert "KeyError" in results[0].message
