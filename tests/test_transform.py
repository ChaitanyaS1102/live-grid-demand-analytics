from datetime import datetime, timezone

from etl.transform import (
    parse_period,
    safe_float,
    normalize_demand_row,
    dedupe_latest_fetch,
    TRACKED_BAS,
)


def test_parse_period_is_tagged_utc_not_naive():
    dt = parse_period("2026-09-30T14")
    assert dt == datetime(2026, 9, 30, 14, tzinfo=timezone.utc)
    assert dt.tzinfo is not None


def test_safe_float_preserves_none_for_missing_reading():
    # EIA returns value=None for a BA that missed a reporting window --
    # that must stay NULL, never silently become 0.0 (which would read
    # as "zero demand," a claim we have no basis for).
    assert safe_float(None) is None
    assert safe_float("") is None
    assert safe_float("nan") is None
    assert safe_float(float("nan")) is None
    assert safe_float("17234") == 17234.0


def test_normalize_demand_row_maps_eia_fields():
    raw = {
        "period": "2026-09-30T14",
        "respondent": "NYIS",
        "respondent-name": "New York Independent System Operator",
        "type": "D",
        "value": "17234",
        "value-units": "megawatthours",
    }
    fetched_at = datetime(2026, 9, 30, 15, tzinfo=timezone.utc)

    norm = normalize_demand_row(raw, fetched_at)

    assert norm["ba_code"] == "NYIS"
    assert norm["period_start"] == datetime(2026, 9, 30, 14, tzinfo=timezone.utc)
    assert norm["demand_mwh"] == 17234.0
    assert norm["fetched_at"] == fetched_at


def test_normalize_demand_row_handles_missing_value():
    raw = {
        "period": "2026-09-30T14",
        "respondent": "CISO",
        "value": None,
    }
    norm = normalize_demand_row(raw, datetime.now(timezone.utc))
    assert norm["demand_mwh"] is None


def test_dedupe_latest_fetch_collapses_by_ba_and_period():
    rows = [
        {"ba_code": "NYIS", "period_start": "2026-09-30T14", "demand_mwh": 100.0, "fetched_at": "t1"},
        {"ba_code": "NYIS", "period_start": "2026-09-30T14", "demand_mwh": 105.0, "fetched_at": "t2"},  # revision, later wins
        {"ba_code": "PJM", "period_start": "2026-09-30T14", "demand_mwh": 500.0, "fetched_at": "t1"},
    ]
    deduped = dedupe_latest_fetch(rows)

    assert len(deduped) == 2
    nyis_row = next(r for r in deduped if r["ba_code"] == "NYIS")
    assert nyis_row["demand_mwh"] == 105.0


def test_tracked_bas_includes_nyis_for_nyc_angle():
    assert "NYIS" in TRACKED_BAS
    assert len(TRACKED_BAS) == 4
