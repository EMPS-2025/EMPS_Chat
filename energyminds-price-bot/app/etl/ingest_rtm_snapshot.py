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
    upsert_rtm_price,
)
from .validators import ensure_numeric, ensure_quarter_range


def ingest_rtm_snapshot(session: Session, file_path: str | Path) -> None:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)

    logger.info("Loading RTM snapshot from %s", path)
    df = pd.read_excel(path)
    df.columns = [str(col).strip().lower() for col in df.columns]

    required = {"date", "hour"}
    if not required.issubset(df.columns):
        raise ValueError("RTM snapshot must contain Date and Hour columns")

    time_block_col = next((col for col in df.columns if "time" in col and "block" in col), None)
    if not time_block_col:
        raise ValueError("RTM snapshot missing time block column")

    mcp_col = next((col for col in df.columns if "mcp" in col), None)
    if not mcp_col:
        raise ValueError("RTM snapshot missing MCP column")

    session_col = next((col for col in df.columns if "session" in col and "id" in col), None)
    mcv_col = next((col for col in df.columns if "mcv" in col), None)
    fsv_col = next((col for col in df.columns if "fsv" in col or "final scheduled" in col), None)

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
        session_id = int(row[session_col]) if session_col and not pd.isna(row[session_col]) else None
        mcv = clean_numeric(row[mcv_col]) if mcv_col else None
        fsv = clean_numeric(row[fsv_col]) if fsv_col else None
        market_day_id = get_or_create_market_day(session, "RTM", trade_date)
        upsert_rtm_price(session, market_day_id, hour, session_id, quarter_index, mcp, mcv_mw=mcv, fsv_mw=fsv)

    logger.info("Completed RTM snapshot ingestion from %s", path)


__all__ = ["ingest_rtm_snapshot"]
