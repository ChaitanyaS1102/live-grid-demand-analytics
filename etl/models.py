"""
SQLAlchemy models for the energy grid intelligence database.

Schema:
    balancing_authorities  -- one row per EIA "respondent" (grid region)
    hourly_demand           -- one row per BA x hour, demand in MW

Unlike a one-time CSV import, this table is fed by a live API that
regularly *revises* recently published hours as utilities submit
corrected meter reads (see etl/transform.py and the README for the
upsert strategy this requires).
"""

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class BalancingAuthority(Base):
    """A grid region EIA calls a 'respondent' (e.g. NYIS, PJM, CISO, ERCO)."""

    __tablename__ = "balancing_authorities"

    code = Column(String, primary_key=True)  # EIA respondent code, e.g. "NYIS"
    name = Column(String, nullable=False)  # EIA respondent-name, e.g. "New York ISO"

    demand_readings = relationship("HourlyDemand", back_populates="authority")


class HourlyDemand(Base):
    __tablename__ = "hourly_demand"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ba_code = Column(String, ForeignKey("balancing_authorities.code"), nullable=False, index=True)
    period_start = Column(DateTime, nullable=False, index=True)  # UTC, hour-aligned

    demand_mwh = Column(Float, nullable=True)  # NULL = EIA has no reading yet for this hour
    fetched_at = Column(DateTime, nullable=False)  # when *we* pulled/refreshed this row

    authority = relationship("BalancingAuthority", back_populates="demand_readings")

    __table_args__ = (
        UniqueConstraint("ba_code", "period_start", name="uq_ba_period"),
    )
