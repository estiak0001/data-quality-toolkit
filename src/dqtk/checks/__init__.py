from .base import Check, CheckResult, Status
from .freshness import FreshnessCheck
from .nulls import NullRateCheck
from .row_count import RowCountCheck
from .schema_drift import SchemaDriftCheck

__all__ = [
    "Check",
    "CheckResult",
    "Status",
    "FreshnessCheck",
    "NullRateCheck",
    "RowCountCheck",
    "SchemaDriftCheck",
]

REGISTRY = {
    "freshness": FreshnessCheck,
    "row_count": RowCountCheck,
    "null_rate": NullRateCheck,
    "schema_drift": SchemaDriftCheck,
}
