"""
Regression test for the "too many SQL variables" bug: a realistic-size
backfill (90 days x 4 regions = 8,640 rows) must upsert successfully in
one load_window() call. Earlier versions pushed the whole batch into a
single INSERT and blew past SQLite's per-statement parameter limit on
some sqlite3 builds (observed in practice on Windows/Python 3.13).

No network access needed -- etl.eia_client.fetch_hourly_demand is
monkeypatched to return a synthetic raw EIA-shaped response instead of
hitting the live API.
"""

import os
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_run.db"
    monkeypatch.setenv("DB_PATH", str(db_file))

    # etl.db reads DB_PATH at import time, so force a fresh import bound
    # to this test's temp file rather than whatever a prior test imported.
    import importlib
    import etl.db as db_module

    importlib.reload(db_module)
    yield db_module


def fake_fetch_hourly_demand(ba_codes, start, end):
    """Stand-in for etl.eia_client.fetch_hourly_demand: synthesizes one
    row per (ba_code, hour) across [start, end), in EIA's raw shape."""
    rows = []
    current = start
    while current < end:
        for code in ba_codes:
            rows.append(
                {
                    "period": current.strftime("%Y-%m-%dT%H"),
                    "respondent": code,
                    "value": "12345",
                }
            )
        current += timedelta(hours=1)
    return rows


def test_backfill_sized_upsert_does_not_exceed_sqlite_variable_limit(temp_db, monkeypatch):
    import etl.run as run_module

    monkeypatch.setattr(run_module, "fetch_hourly_demand", fake_fetch_hourly_demand)
    # ensure_balancing_authorities/load_window import get_session from the
    # reloaded etl.db module via `from etl.db import ... get_session`, so
    # patch run_module's own reference to point at the temp-DB session.
    monkeypatch.setattr(run_module, "get_session", temp_db.get_session)
    monkeypatch.setattr(run_module, "init_db", temp_db.init_db)

    end = datetime(2026, 9, 30, 0, tzinfo=timezone.utc)
    start = end - timedelta(days=90)  # ~90 days x 4 regions = 8,640 rows

    row_count = run_module.load_window(start, end)

    assert row_count == 90 * 24 * len(run_module.TRACKED_BAS)

    session = temp_db.get_session()
    try:
        from etl.models import HourlyDemand

        stored = session.query(HourlyDemand).count()
        assert stored == row_count
    finally:
        session.close()
