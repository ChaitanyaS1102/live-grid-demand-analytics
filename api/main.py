"""
FastAPI backend for the energy grid intelligence platform.

Run with:
    uvicorn api.main:app --reload
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import func

from etl.db import get_session
from etl.models import BalancingAuthority, HourlyDemand
from api.schemas import (
    RegionOut,
    DemandPoint,
    RegionComparison,
    HourOfDayPoint,
    RefreshStatus,
)

app = FastAPI(
    title="Energy Grid Intelligence API",
    description="Hourly electricity demand by US grid region, from EIA's live Open Data API",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/regions", response_model=List[RegionOut])
def list_regions():
    session = get_session()
    try:
        return session.query(BalancingAuthority).order_by(BalancingAuthority.name).all()
    finally:
        session.close()


@app.get("/demand-history/{ba_code}", response_model=List[DemandPoint])
def demand_history(ba_code: str, hours: int = Query(168, description="How many hours back, default 7 days")):
    session = get_session()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        rows = (
            session.query(HourlyDemand)
            .filter(HourlyDemand.ba_code == ba_code.upper(), HourlyDemand.period_start >= cutoff)
            .order_by(HourlyDemand.period_start)
            .all()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="No demand data for this region yet")
        return rows
    finally:
        session.close()


@app.get("/region-comparison", response_model=List[RegionComparison])
def region_comparison(hours: int = Query(168, description="Trailing window in hours, default 7 days")):
    session = get_session()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        q = (
            session.query(
                HourlyDemand.ba_code,
                BalancingAuthority.name,
                func.avg(HourlyDemand.demand_mwh).label("avg_demand"),
                func.max(HourlyDemand.demand_mwh).label("peak_demand"),
                func.min(HourlyDemand.demand_mwh).label("min_demand"),
                func.count(HourlyDemand.id).label("row_count"),
            )
            .join(BalancingAuthority, BalancingAuthority.code == HourlyDemand.ba_code)
            .filter(HourlyDemand.period_start >= cutoff)
            .group_by(HourlyDemand.ba_code, BalancingAuthority.name)
            .order_by(BalancingAuthority.name)
        )
        return [
            RegionComparison(
                ba_code=r.ba_code,
                name=r.name,
                avg_demand_mwh=round(r.avg_demand, 1) if r.avg_demand is not None else None,
                peak_demand_mwh=r.peak_demand,
                min_demand_mwh=r.min_demand,
                row_count=r.row_count,
            )
            for r in q.all()
        ]
    finally:
        session.close()


@app.get("/hour-of-day/{ba_code}", response_model=List[HourOfDayPoint])
def hour_of_day_profile(ba_code: str, hours: int = Query(336, description="Trailing window in hours, default 14 days")):
    """Average demand by hour-of-day (UTC), to show each region's daily
    load curve / peak hours."""
    session = get_session()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        q = (
            session.query(
                func.strftime("%H", HourlyDemand.period_start).label("hod"),
                func.avg(HourlyDemand.demand_mwh).label("avg_demand"),
            )
            .filter(HourlyDemand.ba_code == ba_code.upper(), HourlyDemand.period_start >= cutoff)
            .group_by("hod")
            .order_by("hod")
        )
        results = q.all()
        if not results:
            raise HTTPException(status_code=404, detail="No demand data for this region yet")
        return [
            HourOfDayPoint(
                hour_of_day=int(r.hod),
                avg_demand_mwh=round(r.avg_demand, 1) if r.avg_demand is not None else None,
            )
            for r in results
        ]
    finally:
        session.close()


@app.get("/refresh-status", response_model=List[RefreshStatus])
def refresh_status():
    """How fresh is the data right now, per region -- the point of the
    live-refresh ETL vs. a one-time static import."""
    session = get_session()
    try:
        q = (
            session.query(
                HourlyDemand.ba_code,
                BalancingAuthority.name,
                func.max(HourlyDemand.period_start).label("latest_period"),
                func.max(HourlyDemand.fetched_at).label("last_fetched_at"),
                func.count(HourlyDemand.id).label("row_count"),
            )
            .join(BalancingAuthority, BalancingAuthority.code == HourlyDemand.ba_code)
            .group_by(HourlyDemand.ba_code, BalancingAuthority.name)
            .order_by(BalancingAuthority.name)
        )
        return [
            RefreshStatus(
                ba_code=r.ba_code,
                name=r.name,
                latest_period=r.latest_period,
                last_fetched_at=r.last_fetched_at,
                row_count=r.row_count,
            )
            for r in q.all()
        ]
    finally:
        session.close()
