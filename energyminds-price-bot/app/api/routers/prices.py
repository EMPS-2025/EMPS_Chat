from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db import models

router = APIRouter(tags=["prices"])


class Market(str, Enum):
    DAM = "DAM"
    GDAM = "GDAM"
    RTM = "RTM"


class Aggregate(str, Enum):
    AVG = "avg"
    MIN = "min"
    MAX = "max"


class PriceInputs(BaseModel):
    market: Market
    date: Optional[date] = None
    month: Optional[str] = None
    start_hour: int
    end_hour: int
    weighted: bool
    aggregate: Aggregate


class DailyPriceStat(BaseModel):
    trade_date: date
    price_rs_per_mwh: float
    price_rs_per_kwh: float
    count: int


class PriceResponse(BaseModel):
    inputs: PriceInputs
    price_rs_per_mwh: float
    price_rs_per_kwh: float
    count: int
    daily: Optional[List[DailyPriceStat]] = None


@dataclass
class PricePoint:
    trade_date: date
    value: float
    weight: Optional[float]


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_month(value: Optional[str]) -> Optional[Tuple[date, date]]:
    if not value:
        return None
    month_date = datetime.strptime(value, "%Y-%m").date()
    last_day = monthrange(month_date.year, month_date.month)[1]
    start = month_date.replace(day=1)
    end = month_date.replace(day=last_day)
    return start, end


def _validate_hours(start_hour: int, end_hour: int) -> None:
    if not (0 <= start_hour <= 23 and 1 <= end_hour <= 24):
        raise HTTPException(status_code=400, detail="Hour bounds must be within 0-23 and 1-24")
    if start_hour >= end_hour:
        raise HTTPException(status_code=400, detail="start_hour must be less than end_hour")


def _hour_range_to_quarters(start_hour: int, end_hour: int) -> range:
    return range(start_hour * 4, end_hour * 4)


def _weighted_average(values: Sequence[float], weights: Sequence[Optional[float]]) -> float:
    total_weight = 0.0
    weighted_sum = 0.0
    for value, weight in zip(values, weights):
        w = weight if weight is not None else 0.0
        total_weight += w
        weighted_sum += value * w
    if total_weight == 0:
        return sum(values) / len(values)
    return weighted_sum / total_weight


def _aggregate(values: Sequence[float], aggregate: Aggregate, weights: Optional[Sequence[Optional[float]]] = None) -> float:
    if aggregate == Aggregate.AVG:
        if weights is not None:
            return _weighted_average(values, weights)
        return sum(values) / len(values)
    if aggregate == Aggregate.MIN:
        return min(values)
    if aggregate == Aggregate.MAX:
        return max(values)
    raise HTTPException(status_code=400, detail=f"Unsupported aggregate {aggregate}")


def _collect_dam_points(session: Session, start: date, end: date, start_hour: int, end_hour: int) -> List[PricePoint]:
    stmt = (
        select(models.MarketDay.trade_date, models.DamPrice.hour_block, models.DamPrice.mcp_rs_per_mwh)
        .join(models.DamPrice)
        .where(
            models.MarketDay.market == Market.DAM.value,
            models.MarketDay.trade_date.between(start, end),
            models.DamPrice.hour_block >= start_hour,
            models.DamPrice.hour_block < end_hour,
        )
        .order_by(models.MarketDay.trade_date, models.DamPrice.hour_block)
    )
    results = []
    for trade_date, _, value in session.execute(stmt):
        results.append(PricePoint(trade_date=trade_date, value=float(value), weight=None))
    return results


def _collect_gdam_points(session: Session, start: date, end: date, start_hour: int, end_hour: int, weighted: bool) -> List[PricePoint]:
    quarter_range = _hour_range_to_quarters(start_hour, end_hour)
    stmt = (
        select(
            models.MarketDay.trade_date,
            models.GdamPrice.quarter_index,
            models.GdamPrice.mcp_rs_per_mwh,
            models.GdamPrice.scheduled_volume_mw,
            models.GdamPrice.hydro_fsv_mw,
        )
        .join(models.GdamPrice)
        .where(
            models.MarketDay.market == Market.GDAM.value,
            models.MarketDay.trade_date.between(start, end),
            models.GdamPrice.quarter_index.in_(list(quarter_range)),
        )
        .order_by(models.MarketDay.trade_date, models.GdamPrice.quarter_index)
    )
    points: List[PricePoint] = []
    for trade_date, _, value, scheduled, hydro in session.execute(stmt):
        weight = None
        if weighted:
            weight = float(scheduled) if scheduled is not None else float(hydro) if hydro is not None else None
        points.append(PricePoint(trade_date=trade_date, value=float(value), weight=weight))
    return points


def _collect_rtm_points(session: Session, start: date, end: date, start_hour: int, end_hour: int, weighted: bool) -> List[PricePoint]:
    quarter_range = _hour_range_to_quarters(start_hour, end_hour)
    stmt = (
        select(
            models.MarketDay.trade_date,
            models.RtmPrice.quarter_index,
            models.RtmPrice.mcp_rs_per_mwh,
            models.RtmPrice.fsv_mw,
        )
        .join(models.RtmPrice)
        .where(
            models.MarketDay.market == Market.RTM.value,
            models.MarketDay.trade_date.between(start, end),
            models.RtmPrice.quarter_index.in_(list(quarter_range)),
        )
        .order_by(models.MarketDay.trade_date, models.RtmPrice.quarter_index)
    )
    points: List[PricePoint] = []
    for trade_date, _, value, fsv in session.execute(stmt):
        weight = float(fsv) if weighted and fsv is not None else None
        points.append(PricePoint(trade_date=trade_date, value=float(value), weight=weight))
    return points


def _collect_points(
    session: Session,
    market: Market,
    start: date,
    end: date,
    start_hour: int,
    end_hour: int,
    weighted: bool,
) -> List[PricePoint]:
    if market == Market.DAM:
        return _collect_dam_points(session, start, end, start_hour, end_hour)
    if market == Market.GDAM:
        return _collect_gdam_points(session, start, end, start_hour, end_hour, weighted)
    if market == Market.RTM:
        return _collect_rtm_points(session, start, end, start_hour, end_hour, weighted)
    raise HTTPException(status_code=400, detail=f"Unsupported market {market}")


def _group_by_date(points: Sequence[PricePoint]) -> Dict[date, List[PricePoint]]:
    grouped: Dict[date, List[PricePoint]] = defaultdict(list)
    for point in points:
        grouped[point.trade_date].append(point)
    return grouped


def _summarise_day(points: Sequence[PricePoint], aggregate: Aggregate, weighted: bool) -> Tuple[float, int]:
    values = [p.value for p in points]
    weights = [p.weight for p in points] if weighted else None
    return _aggregate(values, aggregate, weights), len(values)


@router.get("/prices", response_model=PriceResponse)
def get_prices(
    market: Market = Query(..., description="Market type"),
    date_str: Optional[str] = Query(None, alias="date"),
    month_str: Optional[str] = Query(None, alias="month"),
    start_hour: int = Query(0, ge=0, le=23),
    end_hour: int = Query(24, ge=1, le=24),
    weighted: bool = Query(False),
    aggregate: Aggregate = Query(Aggregate.AVG),
    db: Session = Depends(get_db),
) -> PriceResponse:
    _validate_hours(start_hour, end_hour)

    if date_str and month_str:
        raise HTTPException(status_code=400, detail="Provide either date or month, not both")

    date_value = _parse_date(date_str)
    month_range = _parse_month(month_str)

    if not date_value and not month_range:
        raise HTTPException(status_code=400, detail="date or month is required")

    if date_value:
        start = end = date_value
    else:
        start, end = month_range  # type: ignore[misc]

    points = _collect_points(db, market, start, end, start_hour, end_hour, weighted)
    if not points:
        raise HTTPException(status_code=404, detail="No data found for requested window")

    grouped = _group_by_date(points)
    daily_stats: List[DailyPriceStat] = []
    for trade_date, items in sorted(grouped.items()):
        agg_value, count = _summarise_day(items, aggregate, weighted)
        daily_stats.append(
            DailyPriceStat(
                trade_date=trade_date,
                price_rs_per_mwh=round(agg_value, 4),
                price_rs_per_kwh=round(agg_value / 1000, 6),
                count=count,
            )
        )

    if date_value:
        overall = daily_stats[0]
    else:
        overall_values = [stat.price_rs_per_mwh for stat in daily_stats]
        if aggregate == Aggregate.AVG:
            overall_value = sum(overall_values) / len(overall_values)
        elif aggregate == Aggregate.MIN:
            overall_value = min(overall_values)
        else:
            overall_value = max(overall_values)
        overall_count = sum(stat.count for stat in daily_stats)
        overall = DailyPriceStat(
            trade_date=end,
            price_rs_per_mwh=round(overall_value, 4),
            price_rs_per_kwh=round(overall_value / 1000, 6),
            count=overall_count,
        )

    response = PriceResponse(
        inputs=PriceInputs(
            market=market,
            date=date_value,
            month=month_str,
            start_hour=start_hour,
            end_hour=end_hour,
            weighted=weighted,
            aggregate=aggregate,
        ),
        price_rs_per_mwh=overall.price_rs_per_mwh,
        price_rs_per_kwh=overall.price_rs_per_kwh,
        count=overall.count,
        daily=daily_stats if not date_value else None,
    )
    return response


__all__ = ["router"]
