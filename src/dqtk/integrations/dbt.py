import json
from pathlib import Path

from dqtk.checks.base import CheckResult, Status

_DBT_STATUS_MAP = {
    "pass": Status.PASS,
    "warn": Status.WARN,
    "fail": Status.FAIL,
    "error": Status.ERROR,
    "skipped": Status.PASS,
}


def parse_dbt_run_results(run_results_path: str | Path, table: str = "dbt") -> list[CheckResult]:
    """Converts dbt's `target/run_results.json` test results into CheckResults,
    so a `dbt test` run and a `dqtk run` show up side by side in the same
    run-history table and the same Slack/email alert.
    """
    data = json.loads(Path(run_results_path).read_text())
    results = []
    for result in data.get("results", []):
        unique_id = result.get("unique_id", "")
        if not unique_id.startswith("test."):
            continue
        status = _DBT_STATUS_MAP.get(result.get("status", "error"), Status.ERROR)
        message = result.get("message") or f"dbt test {unique_id} -> {result.get('status')}"
        results.append(
            CheckResult(
                check_name=unique_id.split(".")[-1],
                table=table,
                status=status,
                message=message,
                details={
                    "unique_id": unique_id,
                    "execution_time": result.get("execution_time"),
                    "failures": result.get("failures"),
                },
            )
        )
    return results
