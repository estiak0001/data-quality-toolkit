from dqtk.checks.base import CheckResult, Status
from dqtk.storage.run_history import RunHistory


def test_run_lifecycle_persists_results(tmp_path):
    history = RunHistory(f"sqlite:///{tmp_path}/test.db")

    run_id = history.start_run("orders")
    history.record_result(
        run_id,
        CheckResult(
            check_name="row_count",
            table="orders",
            status=Status.PASS,
            message="ok",
            details={"current": 100},
        ),
    )
    history.finish_run(run_id, Status.PASS)

    runs = history.recent_runs()
    assert len(runs) == 1
    assert runs[0].table_name == "orders"
    assert runs[0].status == Status.PASS.value
    assert len(runs[0].results) == 1


def test_row_count_history_returns_oldest_first(tmp_path):
    history = RunHistory(f"sqlite:///{tmp_path}/test.db")

    for count in [100, 110, 90]:
        run_id = history.start_run("orders")
        history.record_result(
            run_id,
            CheckResult(
                check_name="row_count",
                table="orders",
                status=Status.PASS,
                message="ok",
                details={"current": count},
            ),
        )
        history.finish_run(run_id, Status.PASS)

    assert history.row_count_history("orders") == [100, 110, 90]


def test_previous_schema_returns_latest_snapshot(tmp_path):
    history = RunHistory(f"sqlite:///{tmp_path}/test.db")

    run_id = history.start_run("orders")
    history.record_result(
        run_id,
        CheckResult(
            check_name="schema_drift",
            table="orders",
            status=Status.PASS,
            message="ok",
            details={"columns": {"id": "int", "name": "text"}},
        ),
    )
    history.finish_run(run_id, Status.PASS)

    previous = history.previous_schema("orders")
    assert {c.name: c.type for c in previous} == {"id": "int", "name": "text"}


def test_previous_schema_none_when_no_history(tmp_path):
    history = RunHistory(f"sqlite:///{tmp_path}/test.db")
    assert history.previous_schema("orders") is None
