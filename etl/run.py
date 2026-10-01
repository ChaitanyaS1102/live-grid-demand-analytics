"""
Pull hourly demand from EIA's live API and load it into the DB.

Supports two modes:

    # One-time historical backfill (e.g. the last 90 days), for seeding
    # a fresh DB with enough history to chart:
    python -m etl.run --backfill-days 90

    # Incremental refresh, meant to run on a schedule (daily or hourly --
    # see .github/workflows/refresh.yml): re-pulls a rolling recent
    # window and UPSERTS it, because EIA revises recently published
    # hours as utilities submit corrected meter reads. A plain
    # insert-or-ignore (as used in the retail-price-intelligence sibling
    # project, where source rows never change after the fact) would
    # silently keep stale values here.
    python -m etl.run --incremental

Both modes share the same upsert path, so re-running either one against
an already-populated DB is always safe.
"""

import argparse
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

from etl.db import init_db, get_session
from etl.eia_client import fetch_hourly_demand
from etl.models import BalancingAuthority, HourlyDemand
from etl.transform import TRACKED_BAS, dedupe_latest_fetch, normalize_demand_row

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# How far back an incremental refresh re-pulls, to catch revisions EIA
# makes to recently published hours (observed in practice to settle
# within a couple of days, so 48h is a conservative margin from
# the current moment, not from the latest row stored).
INCREMENTAL_WINDOW_HOURS = 48

# SQLite caps the number of "?" parameters in a single statement (older/
# bundled builds -- notably the Python.org Windows build -- default to
# 999). One HourlyDemand row has 4 columns, so a 90-day backfill across 4
# regions (~8,640 rows) would need ~34,500 parameters in one INSERT and
# fail with "too many SQL variables". Sub-batch the upsert well under
# that limit instead, regardless of which sqlite3 build runs it (same
# fix the retail-price-intelligence sibling project uses for its loader).
SQL_VARIABLE_BUDGET = 900


def ensure_balancing_authorities(session) -> None:
    for code, name in TRACKED_BAS.items():
        session.merge(BalancingAuthority(code=code, name=name))
    session.commit()


def load_window(start: datetime, end: datetime) -> int:
    """Fetch and upsert hourly demand for [start, end). Returns row count."""
    init_db()
    session = get_session()
    try:
        ensure_balancing_authorities(session)

        raw_rows = fetch_hourly_demand(TRACKED_BAS.keys(), start, end)
        fetched_at = datetime.now(timezone.utc)
        normalized = [normalize_demand_row(r, fetched_at) for r in raw_rows]
        normalized = dedupe_latest_fetch(normalized)

        if not normalized:
            log.warning("EIA API returned 0 rows for window %s to %s", start, end)
            return 0

        # Upsert: on conflict (ba_code, period_start) UPDATE rather than
        # ignore, so a re-pulled hour that EIA has since revised actually
        # overwrites the stale value instead of keeping it.
        #
        # Sub-batched (see SQL_VARIABLE_BUDGET above) so a large backfill
        # doesn't blow past SQLite's per-statement parameter limit.
        cols_per_row = len(normalized[0])
        sub_batch_size = max(1, SQL_VARIABLE_BUDGET // cols_per_row)

        for i in range(0, len(normalized), sub_batch_size):
            sub_batch = normalized[i : i + sub_batch_size]
            stmt = sqlite_upsert(HourlyDemand.__table__).values(sub_batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ba_code", "period_start"],
                set_={
                    "demand_mwh": stmt.excluded.demand_mwh,
                    "fetched_at": stmt.excluded.fetched_at,
                },
            )
            session.execute(stmt)

        session.commit()

        log.info(
            "Upserted %s hourly demand rows across %s balancing authorities (%s to %s)",
            len(normalized),
            len(TRACKED_BAS),
            start,
            end,
        )
        return len(normalized)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Load EIA hourly demand data.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--backfill-days", type=int, help="One-time historical load, N days back from now.")
    mode.add_argument("--incremental", action="store_true", help="Re-pull and upsert the last 48h (for scheduled refreshes).")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    if args.backfill_days:
        start = now - timedelta(days=args.backfill_days)
        load_window(start, now)
    else:
        start = now - timedelta(hours=INCREMENTAL_WINDOW_HOURS)
        load_window(start, now)


if __name__ == "__main__":
    main()
