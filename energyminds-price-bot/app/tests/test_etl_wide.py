from __future__ import annotations

from sqlalchemy import select

from app.db import models
from app.etl.ingest_damgdam import ingest_damgdam


def test_ingest_wide_workbook(db_session, sample_wide_workbook):
    ingest_damgdam(db_session, sample_wide_workbook)

    dam_count = db_session.execute(select(models.DamPrice)).scalars().all()
    assert len(dam_count) == 6  # 3 hours * 2 days

    gdam_count = db_session.execute(select(models.GdamPrice)).scalars().all()
    assert len(gdam_count) == 8  # 2 hours * 4 quarters * 2 days

    summaries = db_session.execute(select(models.MarketSummary)).scalars().all()
    assert summaries
    labels = {summary.label for summary in summaries}
    assert "RTC" in labels or "Avg.(07-10)" in labels
