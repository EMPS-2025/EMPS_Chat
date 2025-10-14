from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db import models

HOUR_BLOCK_RE = re.compile(r"^(?P<start>\d{2})\s*-\s*(?P<end>\d{2})$")
AVG_LABEL_RE = re.compile(r"^Avg\.\s*\((?P<start>\d{2})-(?P<end>\d{2})\s*Hrs\)", re.IGNORECASE)
TIME_BLOCK_RE = re.compile(r"^(?P<hour>\d{2}):(?P<minute>\d{2})")


def normalise_date(value: object) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, (int, float)):
        return datetime.fromordinal(datetime(1899, 12, 30).toordinal() + int(value)).date()
    if isinstance(value, str):
        return pd.to_datetime(value).date()
    raise ValueError(f"Unsupported date value: {value!r}")


def parse_hour_block(label: str) -> int:
    match = HOUR_BLOCK_RE.match(label.strip())
    if not match:
        raise ValueError(f"Invalid hour block: {label}")
    return int(match.group("start"))


def parse_quarter_index_from_hour(hour_block: int, quarter_offset: int) -> int:
    value = hour_block * 4 + quarter_offset
    if not 0 <= value <= 95:
        raise ValueError(f"Quarter index out of range: {value}")
    return value


def parse_time_block(label: str) -> int:
    match = TIME_BLOCK_RE.match(label.strip())
    if not match:
        raise ValueError(f"Invalid time block label: {label}")
    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    return parse_quarter_index_from_hour(hour, minute // 15)


def clean_numeric(value: object) -> Optional[float]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        return float(value)
    raise ValueError(f"Unable to parse numeric value: {value!r}")


def parse_summary_label(label: str) -> Optional[str]:
    if not label:
        return None
    clean = label.strip()
    if clean.upper() == "RTC":
        return "RTC"
    match = AVG_LABEL_RE.match(clean)
    if match:
        return f"Avg.({match.group('start')}-{match.group('end')})"
    return None


def get_or_create_market_day(session: Session, market: str, trade_date: date) -> int:
    stmt = select(models.MarketDay).where(models.MarketDay.market == market, models.MarketDay.trade_date == trade_date)
    existing = session.execute(stmt).scalar_one_or_none()
    if existing:
        return existing.id
    obj = models.MarketDay(market=market, trade_date=trade_date)
    session.add(obj)
    session.flush()
    return obj.id


def _is_postgres(session: Session) -> bool:
    return session.bind and session.bind.dialect.name == "postgresql"


def upsert_dam_price(session: Session, market_day_id: int, hour_block: int, mcp: float) -> None:
    values = {
        "market_day_id": market_day_id,
        "hour_block": hour_block,
        "mcp_rs_per_mwh": mcp,
    }
    if _is_postgres(session):
        stmt = pg_insert(models.DamPrice).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[models.DamPrice.market_day_id, models.DamPrice.hour_block],
            set_={"mcp_rs_per_mwh": mcp},
        )
        session.execute(stmt)
    else:
        obj = session.query(models.DamPrice).filter_by(market_day_id=market_day_id, hour_block=hour_block).one_or_none()
        if obj:
            obj.mcp_rs_per_mwh = mcp
        else:
            session.add(models.DamPrice(**values))


def upsert_gdam_price(
    session: Session,
    market_day_id: int,
    quarter_index: int,
    mcp: float,
    hydro_fsv_mw: Optional[float] = None,
    scheduled_volume_mw: Optional[float] = None,
) -> None:
    values = {
        "market_day_id": market_day_id,
        "quarter_index": quarter_index,
        "mcp_rs_per_mwh": mcp,
        "hydro_fsv_mw": hydro_fsv_mw,
        "scheduled_volume_mw": scheduled_volume_mw,
    }
    if _is_postgres(session):
        stmt = pg_insert(models.GdamPrice).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[models.GdamPrice.market_day_id, models.GdamPrice.quarter_index],
            set_={
                "mcp_rs_per_mwh": mcp,
                "hydro_fsv_mw": hydro_fsv_mw,
                "scheduled_volume_mw": scheduled_volume_mw,
            },
        )
        session.execute(stmt)
    else:
        obj = (
            session.query(models.GdamPrice)
            .filter_by(market_day_id=market_day_id, quarter_index=quarter_index)
            .one_or_none()
        )
        if obj:
            obj.mcp_rs_per_mwh = mcp
            obj.hydro_fsv_mw = hydro_fsv_mw
            obj.scheduled_volume_mw = scheduled_volume_mw
        else:
            session.add(models.GdamPrice(**values))


def upsert_rtm_price(
    session: Session,
    market_day_id: int,
    hour: int,
    session_id: Optional[int],
    quarter_index: int,
    mcp: float,
    mcv_mw: Optional[float] = None,
    fsv_mw: Optional[float] = None,
) -> None:
    values = {
        "market_day_id": market_day_id,
        "hour": hour,
        "session_id": session_id,
        "quarter_index": quarter_index,
        "mcp_rs_per_mwh": mcp,
        "mcv_mw": mcv_mw,
        "fsv_mw": fsv_mw,
    }
    if _is_postgres(session):
        stmt = pg_insert(models.RtmPrice).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[models.RtmPrice.market_day_id, models.RtmPrice.quarter_index],
            set_={
                "hour": hour,
                "session_id": session_id,
                "mcp_rs_per_mwh": mcp,
                "mcv_mw": mcv_mw,
                "fsv_mw": fsv_mw,
            },
        )
        session.execute(stmt)
    else:
        obj = (
            session.query(models.RtmPrice)
            .filter_by(market_day_id=market_day_id, quarter_index=quarter_index)
            .one_or_none()
        )
        if obj:
            obj.hour = hour
            obj.session_id = session_id
            obj.mcp_rs_per_mwh = mcp
            obj.mcv_mw = mcv_mw
            obj.fsv_mw = fsv_mw
        else:
            session.add(models.RtmPrice(**values))


def upsert_summary(session: Session, market_day_id: int, label: str, value: float) -> None:
    values = {"market_day_id": market_day_id, "label": label, "value": value}
    if _is_postgres(session):
        stmt = pg_insert(models.MarketSummary).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[models.MarketSummary.market_day_id, models.MarketSummary.label],
            set_={"value": value},
        )
        session.execute(stmt)
    else:
        obj = (
            session.query(models.MarketSummary)
            .filter_by(market_day_id=market_day_id, label=label)
            .one_or_none()
        )
        if obj:
            obj.value = value
        else:
            session.add(models.MarketSummary(**values))


__all__ = [
    "normalise_date",
    "parse_hour_block",
    "parse_quarter_index_from_hour",
    "parse_time_block",
    "clean_numeric",
    "parse_summary_label",
    "get_or_create_market_day",
    "upsert_dam_price",
    "upsert_gdam_price",
    "upsert_rtm_price",
    "upsert_summary",
]
