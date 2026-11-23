from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from dqtk.adapters.base import ColumnInfo
from dqtk.checks.base import CheckResult, Status

from .models import Base, CheckResultRow, CheckRun


class RunHistory:
    """Persists check runs/results and answers the baseline questions
    (`row_count_history`, `previous_schema`) that checks need from past runs.
    """

    def __init__(self, dsn: str):
        self.engine = create_engine(dsn)
        Base.metadata.create_all(self.engine)

    def start_run(self, table: str) -> int:
        with Session(self.engine) as session:
            run = CheckRun(
                table_name=table,
                started_at=datetime.now(timezone.utc),
                status=Status.PASS.value,
            )
            session.add(run)
            session.commit()
            return run.id

    def record_result(self, run_id: int, result: CheckResult) -> None:
        with Session(self.engine) as session:
            session.add(
                CheckResultRow(
                    run_id=run_id,
                    check_name=result.check_name,
                    status=result.status.value,
                    message=result.message,
                    details=result.details,
                )
            )
            session.commit()

    def finish_run(self, run_id: int, status: Status) -> None:
        with Session(self.engine) as session:
            run = session.get(CheckRun, run_id)
            run.finished_at = datetime.now(timezone.utc)
            run.status = status.value
            session.commit()

    def row_count_history(self, table: str, limit: int = 7, before_run_id: int | None = None) -> list[int]:
        with Session(self.engine) as session:
            stmt = (
                select(CheckResultRow)
                .join(CheckRun)
                .where(CheckRun.table_name == table)
                .where(CheckResultRow.check_name == "row_count")
                .order_by(CheckRun.started_at.desc())
                .limit(limit)
            )
            if before_run_id is not None:
                stmt = stmt.where(CheckRun.id < before_run_id)
            rows = session.execute(stmt).scalars().all()
        counts = [r.details.get("current") for r in rows if r.details.get("current") is not None]
        return list(reversed(counts))

    def previous_schema(self, table: str, before_run_id: int | None = None) -> list[ColumnInfo] | None:
        with Session(self.engine) as session:
            stmt = (
                select(CheckResultRow)
                .join(CheckRun)
                .where(CheckRun.table_name == table)
                .where(CheckResultRow.check_name == "schema_drift")
                .order_by(CheckRun.started_at.desc())
                .limit(1)
            )
            if before_run_id is not None:
                stmt = stmt.where(CheckRun.id < before_run_id)
            row = session.execute(stmt).scalars().first()
        if row is None:
            return None
        return [ColumnInfo(name=n, type=t) for n, t in row.details.get("columns", {}).items()]

    def recent_runs(self, limit: int = 50) -> list[CheckRun]:
        with Session(self.engine) as session:
            stmt = select(CheckRun).order_by(CheckRun.started_at.desc()).limit(limit)
            runs = session.execute(stmt).scalars().all()
            for run in runs:
                _ = run.results  # noqa: F841  load within session
                session.expunge(run)
        return list(runs)

    def close(self) -> None:
        self.engine.dispose()
