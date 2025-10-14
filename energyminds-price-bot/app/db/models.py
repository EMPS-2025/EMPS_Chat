from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class MarketDay(Base):
    __tablename__ = "market_day"

    id: Mapped[int] = mapped_column(primary_key=True)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (UniqueConstraint("market", "trade_date", name="uq_market_trade_date"),)

    dam_prices: Mapped[list[DamPrice]] = relationship(back_populates="market_day", cascade="all, delete-orphan")
    gdam_prices: Mapped[list[GdamPrice]] = relationship(back_populates="market_day", cascade="all, delete-orphan")
    rtm_prices: Mapped[list[RtmPrice]] = relationship(back_populates="market_day", cascade="all, delete-orphan")
    summaries: Mapped[list[MarketSummary]] = relationship(back_populates="market_day", cascade="all, delete-orphan")


class DamPrice(Base):
    __tablename__ = "dam_price"

    id: Mapped[int] = mapped_column(primary_key=True)
    market_day_id: Mapped[int] = mapped_column(ForeignKey("market_day.id", ondelete="CASCADE"), nullable=False)
    hour_block: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    mcp_rs_per_mwh: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("hour_block BETWEEN 0 AND 23", name="ck_dam_hour_block"),
        UniqueConstraint("market_day_id", "hour_block", name="dam_uniq"),
        Index("idx_dam_mday_hour", "market_day_id", "hour_block"),
    )

    market_day: Mapped[MarketDay] = relationship(back_populates="dam_prices")


class GdamPrice(Base):
    __tablename__ = "gdam_price"

    id: Mapped[int] = mapped_column(primary_key=True)
    market_day_id: Mapped[int] = mapped_column(ForeignKey("market_day.id", ondelete="CASCADE"), nullable=False)
    quarter_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    mcp_rs_per_mwh: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    hydro_fsv_mw: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    scheduled_volume_mw: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    __table_args__ = (
        CheckConstraint("quarter_index BETWEEN 0 AND 95", name="ck_gdam_quarter"),
        UniqueConstraint("market_day_id", "quarter_index", name="gdam_uniq"),
        Index("idx_gdam_mday_q", "market_day_id", "quarter_index"),
    )

    market_day: Mapped[MarketDay] = relationship(back_populates="gdam_prices")


class RtmPrice(Base):
    __tablename__ = "rtm_price"

    id: Mapped[int] = mapped_column(primary_key=True)
    market_day_id: Mapped[int] = mapped_column(ForeignKey("market_day.id", ondelete="CASCADE"), nullable=False)
    hour: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    session_id: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    quarter_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    mcv_mw: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    fsv_mw: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    mcp_rs_per_mwh: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("hour BETWEEN 1 AND 24", name="ck_rtm_hour"),
        CheckConstraint("quarter_index BETWEEN 0 AND 95", name="ck_rtm_quarter"),
        UniqueConstraint("market_day_id", "quarter_index", name="rtm_uniq"),
        Index("idx_rtm_mday_q", "market_day_id", "quarter_index"),
    )

    market_day: Mapped[MarketDay] = relationship(back_populates="rtm_prices")


class MarketSummary(Base):
    __tablename__ = "market_summary"

    id: Mapped[int] = mapped_column(primary_key=True)
    market_day_id: Mapped[int] = mapped_column(ForeignKey("market_day.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)

    __table_args__ = (UniqueConstraint("market_day_id", "label", name="uq_summary_label"),)

    market_day: Mapped[MarketDay] = relationship(back_populates="summaries")


__all__ = [
    "MarketDay",
    "DamPrice",
    "GdamPrice",
    "RtmPrice",
    "MarketSummary",
]
