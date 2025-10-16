from __future__ import annotations

import os
from collections.abc import Generator

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base


@pytest.fixture(scope="session")
def engine() -> Generator:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    try:
        yield session
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def sample_wide_workbook(tmp_path) -> str:
    dam_rows = [
        ["", "2024-08-01", "2024-08-02"],
        ["00 - 01", 100, 90],
        ["01 - 02", 110, 95],
        ["02 - 03", 120, 105],
        ["RTC", 105, 100],
    ]
    gdam_rows = [
        ["", "2024-08-01", "2024-08-02"],
        ["00 - 01", 200, 210],
        ["01 - 02", 220, 225],
        ["Avg. (07-10 Hrs)", 215, 220],
    ]
    path = tmp_path / "wide.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame(dam_rows).to_excel(writer, sheet_name="DAM", index=False, header=False)
        pd.DataFrame(gdam_rows).to_excel(writer, sheet_name="GDAM", index=False, header=False)
    return str(path)
