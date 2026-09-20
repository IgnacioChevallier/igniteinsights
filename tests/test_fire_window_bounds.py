"""The FIRMS window a run asks for has to be bounded on both ends.

`get_active_fires` took only `since`. Preparation used it to pick `ignition_datetime`,
which anchors ELMFIRE's TSTART — so a single detection ingested weeks after the requested
window silently became the ignition time. The run then asked for hundreds of weather bands
it did not have, `validate_weather_coverage` raised, and preparation died *after* writing
every raster but before the namelist: the panel got an inputs folder with no elmfire.data
and no simulation to show.

No DB here — the query itself is the thing under test.
"""
import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from app.db import repository


class _CapturingSession:
    """Stands in for AsyncSession: records the statement, answers with no rows."""

    def __init__(self):
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return _EmptyResult()


class _EmptyResult:
    def all(self):
        return []


def _compiled(statement) -> str:
    return str(statement.compile(compile_kwargs={"literal_binds": True}))


def test_until_bounds_the_window_on_both_ends():
    # No pytest-asyncio in this project's test deps, and one coroutine does not earn one.
    session = _CapturingSession()
    since = datetime(2026, 2, 7, tzinfo=UTC)

    asyncio.run(
        repository.get_active_fires(
            session, since=since, aoi_id=uuid.uuid4(), until=since + timedelta(days=1)
        )
    )

    sql = _compiled(session.statement)
    assert "acq_datetime >=" in sql, "lower bound lost"
    assert "acq_datetime <" in sql.replace("acq_datetime <=", ""), (
        "upper bound lost: detections after the requested window would set the ignition time"
    )


def test_without_until_the_query_stays_open_ended():
    # The dashboard's "last N hours" view has no end, and must keep working.
    session = _CapturingSession()

    asyncio.run(
        repository.get_active_fires(session, since=datetime(2026, 2, 7, tzinfo=UTC))
    )

    sql = _compiled(session.statement)
    assert "acq_datetime >=" in sql
    # `acq_datetime` also appears in the SELECT list, so the check is on the bound itself.
    assert "acq_datetime <" not in sql
