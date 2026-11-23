from datetime import datetime, timedelta, timezone

from dqtk.adapters.base import ColumnInfo
from dqtk.checks import FreshnessCheck, NullRateCheck, RowCountCheck, SchemaDriftCheck
from dqtk.checks.base import Status

from .conftest import FakeAdapter


def test_freshness_pass_when_recent():
    now = datetime.now(timezone.utc)
    adapter = FakeAdapter(max_values={("orders", "updated_at"): now - timedelta(minutes=5)})
    result = FreshnessCheck(column="updated_at", max_age_minutes=60).run(adapter, "orders")
    assert result.status == Status.PASS


def test_freshness_fail_when_stale():
    now = datetime.now(timezone.utc)
    adapter = FakeAdapter(max_values={("orders", "updated_at"): now - timedelta(minutes=120)})
    result = FreshnessCheck(column="updated_at", max_age_minutes=60).run(adapter, "orders")
    assert result.status == Status.FAIL
    assert "stale" in result.message


def test_freshness_error_on_unparseable_value():
    adapter = FakeAdapter(max_values={("orders", "updated_at"): "not-a-date"})
    result = FreshnessCheck(column="updated_at", max_age_minutes=60).run(adapter, "orders")
    assert result.status == Status.ERROR


def test_row_count_passes_with_insufficient_history():
    adapter = FakeAdapter(row_counts={"orders": 1000})
    result = RowCountCheck(max_pct_change=0.2, min_history=3).run(adapter, "orders", history=[1000])
    assert result.status == Status.PASS
    assert "not enough history" in result.message


def test_row_count_passes_within_threshold():
    adapter = FakeAdapter(row_counts={"orders": 1050})
    result = RowCountCheck(max_pct_change=0.2).run(adapter, "orders", history=[1000, 990, 1010])
    assert result.status == Status.PASS


def test_row_count_fails_on_big_drop():
    adapter = FakeAdapter(row_counts={"orders": 100})
    result = RowCountCheck(max_pct_change=0.2).run(adapter, "orders", history=[1000, 990, 1010])
    assert result.status == Status.FAIL
    assert result.details["current"] == 100


def test_null_rate_pass_and_fail():
    adapter = FakeAdapter(null_rates={("orders", "customer_id"): 0.0})
    assert NullRateCheck("customer_id", 0.01).run(adapter, "orders").status == Status.PASS

    adapter = FakeAdapter(null_rates={("orders", "customer_id"): 0.5})
    result = NullRateCheck("customer_id", 0.01).run(adapter, "orders")
    assert result.status == Status.FAIL


def test_schema_drift_no_baseline_passes():
    adapter = FakeAdapter(schemas={"orders": [ColumnInfo("id", "int")]})
    result = SchemaDriftCheck().run(adapter, "orders", previous_columns=None)
    assert result.status == Status.PASS


def test_schema_drift_detects_added_column():
    adapter = FakeAdapter(schemas={"orders": [ColumnInfo("id", "int"), ColumnInfo("note", "text")]})
    result = SchemaDriftCheck().run(adapter, "orders", previous_columns=[ColumnInfo("id", "int")])
    assert result.status == Status.WARN
    assert result.details["added"] == ["note"]


def test_schema_drift_detects_type_change_as_fail():
    adapter = FakeAdapter(schemas={"orders": [ColumnInfo("id", "text")]})
    result = SchemaDriftCheck().run(adapter, "orders", previous_columns=[ColumnInfo("id", "int")])
    assert result.status == Status.FAIL
    assert result.details["type_changed"] == ["id"]


def test_schema_drift_detects_removed_column_as_fail():
    adapter = FakeAdapter(schemas={"orders": [ColumnInfo("id", "int")]})
    result = SchemaDriftCheck().run(
        adapter, "orders", previous_columns=[ColumnInfo("id", "int"), ColumnInfo("note", "text")]
    )
    assert result.status == Status.FAIL
    assert result.details["removed"] == ["note"]
