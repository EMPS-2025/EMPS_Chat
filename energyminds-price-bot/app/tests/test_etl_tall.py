from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from app.db import models
from app.etl.ingest_dam_snapshot import ingest_dam_snapshot
from app.etl.ingest_gdam_snapshot import ingest_gdam_snapshot
from app.etl.ingest_rtm_snapshot import ingest_rtm_snapshot


def _write_excel(path, data):
    df = pd.DataFrame(data)
    df.to_excel(path, index=False)


def test_ingest_dam_snapshot(tmp_path, db_session):
    path = tmp_path / "dam.xlsx"
    _write_excel(
        path,
        {
            "Date": ["2024-08-01", "2024-08-01"],
            "Hour": [1, 2],
            "Weighted MCP (Rs/MWh)": [100, 120],
        },
    )
    ingest_dam_snapshot(db_session, path)
    prices = db_session.execute(select(models.DamPrice)).scalars().all()
    assert len(prices) == 2
    assert {float(p.mcp_rs_per_mwh) for p in prices} == {100.0, 120.0}


def test_ingest_gdam_snapshot(tmp_path, db_session):
    path = tmp_path / "gdam.xlsx"
    _write_excel(
        path,
        {
            "Date": ["2024-08-01", "2024-08-01"],
            "Hour": [0, 0],
            "Time Block": ["00:00 - 00:15", "00:15 - 00:30"],
            "MCP (Rs/MWh)": [200, 210],
            "Scheduled Volume (MW)": [10, 20],
        },
    )
    ingest_gdam_snapshot(db_session, path)
    prices = db_session.execute(select(models.GdamPrice)).scalars().all()
    assert len(prices) == 2
    assert {float(p.mcp_rs_per_mwh) for p in prices} == {200.0, 210.0}


def test_ingest_rtm_snapshot(tmp_path, db_session):
    path = tmp_path / "rtm.xlsx"
    _write_excel(
        path,
        {
            "Date": ["2024-08-01"],
            "Hour": [1],
            "Session ID": [2],
            "Time Block": ["00:00 - 00:15"],
            "MCP (Rs/MWh)": [300],
            "Final Scheduled Volume (MW)": [15],
        },
    )
    ingest_rtm_snapshot(db_session, path)
    prices = db_session.execute(select(models.RtmPrice)).scalars().all()
    assert len(prices) == 1
    assert float(prices[0].mcp_rs_per_mwh) == 300.0
