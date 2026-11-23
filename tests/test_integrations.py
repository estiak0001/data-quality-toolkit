import json

from dqtk.checks.base import Status
from dqtk.integrations.dbt import parse_dbt_run_results
from dqtk.integrations.great_expectations import parse_ge_checkpoint_result


def test_parse_dbt_run_results(tmp_path):
    run_results = {
        "results": [
            {"unique_id": "test.my_project.not_null_orders_id", "status": "pass", "execution_time": 0.1},
            {
                "unique_id": "test.my_project.unique_orders_id",
                "status": "fail",
                "message": "2 records failed",
                "execution_time": 0.2,
                "failures": 2,
            },
            {"unique_id": "model.my_project.stg_orders", "status": "success"},
        ]
    }
    path = tmp_path / "run_results.json"
    path.write_text(json.dumps(run_results))

    results = parse_dbt_run_results(path, table="orders")

    assert len(results) == 2  # the model result is filtered out
    assert results[0].status == Status.PASS
    assert results[1].status == Status.FAIL
    assert results[1].details["failures"] == 2


def test_parse_ge_checkpoint_result():
    checkpoint_result = {
        "run_results": {
            "validation_1": {
                "validation_result": {
                    "results": [
                        {
                            "success": True,
                            "expectation_config": {
                                "expectation_type": "expect_column_values_to_not_be_null",
                                "kwargs": {"column": "id"},
                            },
                            "result": {},
                        },
                        {
                            "success": False,
                            "expectation_config": {
                                "expectation_type": "expect_column_values_to_be_unique",
                                "kwargs": {"column": "id"},
                            },
                            "result": {"unexpected_count": 3},
                        },
                    ]
                }
            }
        }
    }

    results = parse_ge_checkpoint_result(checkpoint_result, table="orders")

    assert len(results) == 2
    assert results[0].status == Status.PASS
    assert results[1].status == Status.FAIL
    assert results[1].details["result"]["unexpected_count"] == 3
