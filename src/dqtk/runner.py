import logging

from dqtk.checks.base import CheckResult, Status
from dqtk.config import DqtkConfig
from dqtk.storage.run_history import RunHistory

logger = logging.getLogger("dqtk")


def run_table(history: RunHistory, config: DqtkConfig, table_config) -> list[CheckResult]:
    adapter = config.adapters[table_config.adapter_name]
    table = table_config.name

    run_id = history.start_run(table)
    results: list[CheckResult] = []
    worst = Status.PASS

    for check in table_config.checks:
        context = {
            "history": history.row_count_history(table, before_run_id=run_id),
            "previous_columns": history.previous_schema(table, before_run_id=run_id),
        }
        try:
            result = check.run(adapter, table, **context)
        except Exception as exc:  # a broken check must not crash the whole run
            result = CheckResult(
                check_name=check.name,
                table=table,
                status=Status.ERROR,
                message=f"check raised {type(exc).__name__}: {exc}",
            )
        results.append(result)
        history.record_result(run_id, result)
        if _severity(result.status) > _severity(worst):
            worst = result.status
        logger.info("%s %s: %s", table, result.check_name, result.message)

    history.finish_run(run_id, worst)
    return results


def _severity(status: Status) -> int:
    return {Status.PASS: 0, Status.WARN: 1, Status.FAIL: 2, Status.ERROR: 3}[status]


def run_all(config: DqtkConfig) -> dict[str, list[CheckResult]]:
    history = RunHistory(config.storage_dsn)
    outcomes: dict[str, list[CheckResult]] = {}
    try:
        for table_config in config.tables:
            results = run_table(history, config, table_config)
            outcomes[table_config.name] = results

            non_passing = [r for r in results if r.status != Status.PASS]
            for notifier in config.notifiers:
                notifier.notify(table_config.name, non_passing)
    finally:
        history.close()
    return outcomes
