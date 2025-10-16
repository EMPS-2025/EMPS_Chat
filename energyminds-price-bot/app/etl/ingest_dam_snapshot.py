from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session

from .parse_common import clean_numeric, get_or_create_market_day, normalise_date, upsert_dam_price
from .validators import ensure_hour_range, ensure_numeric


def ingest_dam_snapshot(session: Session, file_path: str | Path) -> None:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)

    logger.info("Loading DAM snapshot from %s", path)
    df = pd.read_excel(path)
    df.columns = [str(col).strip().lower() for col in df.columns]

    if "date" not in df.columns or "hour" not in df.columns:
        raise ValueError("DAM snapshot must contain 'Date' and 'Hour' columns")

    mcp_col = next((col for col in df.columns if "mcp" in col), None)
    if not mcp_col:
        raise ValueError("DAM snapshot missing MCP column")

    for _, row in df.iterrows():
        trade_date = normalise_date(row["date"])
        hour = int(row["hour"])
        hour_block = hour - 1
        ensure_hour_range(hour_block)
        mcp = clean_numeric(row[mcp_col])
        if mcp is None:
            continue
        ensure_numeric(mcp, min_value=0)
        market_day_id = get_or_create_market_day(session, "DAM", trade_date)
        upsert_dam_price(session, market_day_id, hour_block, mcp)

    logger.info("Completed DAM snapshot ingestion from %s", path)


__all__ = ["ingest_dam_snapshot"]
