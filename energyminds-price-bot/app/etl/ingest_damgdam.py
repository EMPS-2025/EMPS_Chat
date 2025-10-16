from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session

from .parse_common import (
    clean_numeric,
    get_or_create_market_day,
    normalise_date,
    parse_hour_block,
    parse_quarter_index_from_hour,
    parse_summary_label,
    upsert_dam_price,
    upsert_gdam_price,
    upsert_summary,
)
from .validators import ValidationError, ensure_hour_range, ensure_numeric, ensure_quarter_range

DAM_SHEET = "DAM"
GDAM_SHEET = "GDAM"


def _extract_dates(df: pd.DataFrame) -> Dict[int, pd.Timestamp]:
    dates: Dict[int, pd.Timestamp] = {}
    for col in range(1, df.shape[1]):
        value = df.iat[0, col]
        if pd.isna(value):
            continue
        try:
            dates[col] = normalise_date(value)
        except Exception as exc:  # pragma: no cover - logged for visibility
            logger.warning("Skipping column %s due to invalid date header: %s", col, exc)
    return dates


def _process_summary_row(session: Session, market: str, label: str, df: pd.DataFrame, row_index: int, dates: Dict[int, pd.Timestamp]) -> None:
    summary_label = parse_summary_label(label)
    if not summary_label:
        return
    for col_idx, trade_date in dates.items():
        raw_value = df.iat[row_index, col_idx]
        value = clean_numeric(raw_value)
        if value is None:
            continue
        market_day_id = get_or_create_market_day(session, market, trade_date)
        upsert_summary(session, market_day_id, summary_label, value)


def _process_dam_sheet(session: Session, df: pd.DataFrame) -> None:
    dates = _extract_dates(df)
    for row_index in range(1, df.shape[0]):
        label = df.iat[row_index, 0]
        if pd.isna(label):
            continue
        label_str = str(label).strip()
        try:
            hour_block = parse_hour_block(label_str)
            ensure_hour_range(hour_block)
        except Exception:
            _process_summary_row(session, "DAM", label_str, df, row_index, dates)
            continue

        for col_idx, trade_date in dates.items():
            raw_value = df.iat[row_index, col_idx]
            mcp = clean_numeric(raw_value)
            if mcp is None:
                continue
            ensure_numeric(mcp, min_value=0)
            market_day_id = get_or_create_market_day(session, "DAM", trade_date)
            upsert_dam_price(session, market_day_id, hour_block, mcp)


def _process_gdam_sheet(session: Session, df: pd.DataFrame) -> None:
    dates = _extract_dates(df)
    for row_index in range(1, df.shape[0]):
        label = df.iat[row_index, 0]
        if pd.isna(label):
            continue
        label_str = str(label).strip()
        try:
            hour_block = parse_hour_block(label_str)
            ensure_hour_range(hour_block)
        except Exception:
            _process_summary_row(session, "GDAM", label_str, df, row_index, dates)
            continue

        for col_idx, trade_date in dates.items():
            raw_value = df.iat[row_index, col_idx]
            mcp = clean_numeric(raw_value)
            if mcp is None:
                continue
            ensure_numeric(mcp, min_value=0)
            market_day_id = get_or_create_market_day(session, "GDAM", trade_date)
            for quarter_offset in range(4):
                quarter_index = parse_quarter_index_from_hour(hour_block, quarter_offset)
                ensure_quarter_range(quarter_index)
                upsert_gdam_price(session, market_day_id, quarter_index, mcp)


def ingest_damgdam(session: Session, file_path: str | Path) -> None:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)

    workbook = pd.ExcelFile(path)
    if DAM_SHEET not in workbook.sheet_names or GDAM_SHEET not in workbook.sheet_names:
        raise ValidationError("DAMGDAM workbook must contain DAM and GDAM sheets")

    logger.info("Starting DAM sheet ingestion from %s", path)
    df_dam = workbook.parse(DAM_SHEET, header=None)
    _process_dam_sheet(session, df_dam)

    logger.info("Starting GDAM sheet ingestion from %s", path)
    df_gdam = workbook.parse(GDAM_SHEET, header=None)
    _process_gdam_sheet(session, df_gdam)

    logger.info("Completed ingestion for %s", path)


__all__ = ["ingest_damgdam"]
