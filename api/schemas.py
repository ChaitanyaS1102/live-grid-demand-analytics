"""Pydantic response models for the API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RegionOut(BaseModel):
    code: str
    name: str

    class Config:
        from_attributes = True


class DemandPoint(BaseModel):
    period_start: datetime
    demand_mwh: Optional[float] = None


class RegionComparison(BaseModel):
    ba_code: str
    name: str
    avg_demand_mwh: Optional[float] = None
    peak_demand_mwh: Optional[float] = None
    min_demand_mwh: Optional[float] = None
    row_count: int


class HourOfDayPoint(BaseModel):
    hour_of_day: int  # 0-23, UTC
    avg_demand_mwh: Optional[float] = None


class RefreshStatus(BaseModel):
    ba_code: str
    name: str
    latest_period: Optional[datetime] = None
    last_fetched_at: Optional[datetime] = None
    row_count: int
