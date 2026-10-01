"""
Pure transform functions for the ETL pipeline. Kept free of any I/O
(no HTTP or DB access) so they're easy to unit test in isolation.
"""

from datetime import datetime, timezone


# EIA "respondent" codes we track, mapped to their display names.
# All four are real EIA balancing-authority/RTO codes for
# electricity/rto/region-data; NYIS keeps a tie back to the original
# NYC angle, the other three give a meaningful cross-region comparison.
TRACKED_BAS = {
    "NYIS": "New York ISO",
    "PJM": "PJM Interconnection",
    "CISO": "California ISO",
    "ERCO": "ERCOT (Texas)",
}


def parse_period(period: str) -> datetime:
    """Parse an EIA 'period' string into a UTC datetime.

    EIA's electricity/rto/region-data endpoint returns period as an
    hour-resolution ISO-8601-ish string with no UTC offset, e.g.
    "2026-09-30T14". Per EIA's documentation this series is already
    normalized to UTC (so demand across different-timezone BAs lines
    up on the same clock) -- it is NOT each respondent's local time.
    We parse it at face value and tag it UTC rather than silently
    treating it as naive/local, which would make cross-BA comparisons
    (e.g. NYIS vs. CISO) wrong by several hours.
    """
    dt = datetime.strptime(period, "%Y-%m-%dT%H")
    return dt.replace(tzinfo=timezone.utc)


def safe_float(value):
    """Return a float, or None if the value is missing/null/unparseable.

    EIA's hourly demand series has real gaps: a respondent can miss a
    reporting window and that hour comes back with value=None rather
    than 0. Coercing that to 0.0 would read as "zero demand," which is
    never actually true for a grid region -- so missing stays NULL.
    """
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except (ValueError, TypeError):
        return None
    if f != f:  # NaN check without importing math
        return None
    return f


def normalize_demand_row(raw: dict, fetched_at: datetime) -> dict:
    """Map one raw EIA API row into our storage shape.

    Expects the shape EIA's v2 API returns under response.data:
    {"period": "2026-09-30T14", "respondent": "NYIS",
     "respondent-name": "New York Independent System Operator",
     "type": "D", "value": "17234", "value-units": "megawatthours"}
    """
    return {
        "ba_code": raw["respondent"],
        "period_start": parse_period(raw["period"]),
        "demand_mwh": safe_float(raw.get("value")),
        "fetched_at": fetched_at,
    }


def dedupe_latest_fetch(rows: list[dict]) -> list[dict]:
    """Collapse rows to one per (ba_code, period_start), keeping the last.

    A single fetch window can re-request hours it already pulled this
    run (the incremental refresh deliberately over-fetches the last
    48h to catch revisions -- see etl/run.py), and EIA itself can
    return more than one row for the same respondent/period across
    paginated requests. Last-one-wins here; the real "which value is
    newest" authority is always the live API, re-pulled on the next
    scheduled refresh, not something resolved by timestamp order
    within one run.
    """
    deduped = {}
    for row in rows:
        key = (row["ba_code"], row["period_start"])
        deduped[key] = row
    return list(deduped.values())
