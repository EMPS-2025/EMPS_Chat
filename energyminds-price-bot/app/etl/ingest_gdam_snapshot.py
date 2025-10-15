from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session

from .parse_common import (
    clean_numeric,
    get_or_create_market_day,
    normalise_date,
    parse_time_block,
    upsert_gdam_price,
)
from .validators import ensure_numeric, ensure_quarter_range


def ingest_gdam_snapshot(session: Session, file_path: str | Path) -> None:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)

    logger.info("Loading GDAM snapshot from %s", path)
    df = pd.read_excel(path)
    df.columns = [str(col).strip().lower() for col in df.columns]

    required = {"date", "hour"}
    if not required.issubset(df.columns):
        raise ValueError("GDAM snapshot must contain Date and Hour columns")

    time_block_col = next((col for col in df.columns if "time" in col and "block" in col), None)
    if not time_block_col:
        raise ValueError("GDAM snapshot missing time block column")

    mcp_col = next((col for col in df.columns if "mcp" in col), None)
    if not mcp_col:
        raise ValueError("GDAM snapshot missing MCP column")

    hydro_col = next((col for col in df.columns if "hydro" in col and "fsv" in col), None)
    volume_col = next((col for col in df.columns if "scheduled" in col and "volume" in col), None)

    for _, row in df.iterrows():
        trade_date = normalise_date(row["date"])
        hour = int(row["hour"])
        time_label = row[time_block_col]
        quarter_index = parse_time_block(str(time_label))
        ensure_quarter_range(quarter_index)
        mcp = clean_numeric(row[mcp_col])
        if mcp is None:
            continue
        ensure_numeric(mcp, min_value=0)
        hydro = clean_numeric(row[hydro_col]) if hydro_col else None
        volume = clean_numeric(row[volume_col]) if volume_col else None
        market_day_id = get_or_create_market_day(session, "GDAM", trade_date)
        upsert_gdam_price(session, market_day_id, quarter_index, mcp, hydro_fsv_mw=hydro, scheduled_volume_mw=volume)

    logger.info("Completed GDAM snapshot ingestion from %s", path)


__all__ = ["ingest_gdam_snapshot"]
