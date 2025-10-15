from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.main import app
from app.etl.ingest_damgdam import ingest_damgdam
from app.etl.ingest_gdam_snapshot import ingest_gdam_snapshot


@pytest.fixture()
def client(db_session, sample_wide_workbook):
    ingest_damgdam(db_session, sample_wide_workbook)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_dam_price_window(client):
    response = client.get(
        "/api/prices",
        params={
            "market": "DAM",
            "date": "2024-08-01",
            "start_hour": 0,
            "end_hour": 3,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["price_rs_per_mwh"] == 110.0
    assert data["count"] == 3


def test_gdam_weighted_average(client, db_session, tmp_path):
    path = tmp_path / "gdam_snapshot.xlsx"
    df = pd.DataFrame(
        {
            "Date": ["2024-08-01", "2024-08-01", "2024-08-01", "2024-08-01"],
            "Hour": [0, 0, 1, 1],
            "Time Block": ["00:00 - 00:15", "00:15 - 00:30", "01:00 - 01:15", "01:15 - 01:30"],
            "MCP (Rs/MWh)": [100, 200, 300, 400],
            "Scheduled Volume (MW)": [10, 10, 5, 15],
        }
    )
    df.to_excel(path, index=False)
    ingest_gdam_snapshot(db_session, path)

    simple = client.get(
        "/api/prices",
        params={
            "market": "GDAM",
            "date": "2024-08-01",
            "start_hour": 0,
            "end_hour": 2,
        },
    )
    weighted = client.get(
        "/api/prices",
        params={
            "market": "GDAM",
            "date": "2024-08-01",
            "start_hour": 0,
            "end_hour": 2,
            "weighted": True,
        },
    )

    assert simple.status_code == 200
    assert weighted.status_code == 200

    simple_value = simple.json()["price_rs_per_mwh"]
    weighted_value = weighted.json()["price_rs_per_mwh"]

    assert simple_value != weighted_value
    assert weighted_value == pytest.approx(233.3333, rel=1e-3)


def test_monthly_aggregation(client):
    response = client.get(
        "/api/prices",
        params={
            "market": "DAM",
            "month": "2024-08",
            "start_hour": 0,
            "end_hour": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["daily"]
    assert len(data["daily"]) == 2
