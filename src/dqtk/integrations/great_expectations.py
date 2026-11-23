from typing import Any

from dqtk.checks.base import CheckResult, Status


def parse_ge_checkpoint_result(checkpoint_result: Any, table: str = "ge") -> list[CheckResult]:
    """Converts a Great Expectations CheckpointResult into CheckResults.

    Takes the already-run `checkpoint_result` object (or its `.to_json_dict()`
    dict form) rather than importing/running `great_expectations` itself, so
    this module has no hard dependency on the `great_expectations` package —
    only projects that already use GE need to install it.
    """
    as_dict = (
        checkpoint_result.to_json_dict()
        if hasattr(checkpoint_result, "to_json_dict")
        else checkpoint_result
    )

    results = []
    for run_result in as_dict.get("run_results", {}).values():
        validation = run_result.get("validation_result", {})
        for expectation_result in validation.get("results", []):
            config = expectation_result.get("expectation_config", {})
            expectation_type = config.get("expectation_type", "unknown_expectation")
            success = expectation_result.get("success", False)
            results.append(
                CheckResult(
                    check_name=expectation_type,
                    table=table,
                    status=Status.PASS if success else Status.FAIL,
                    message=f"{expectation_type} -> {'passed' if success else 'failed'}",
                    details={
                        "kwargs": config.get("kwargs", {}),
                        "result": expectation_result.get("result", {}),
                    },
                )
            )
    return results
