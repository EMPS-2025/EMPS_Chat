from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.etl.ingest_dam_snapshot import ingest_dam_snapshot
from app.etl.ingest_damgdam import ingest_damgdam
from app.etl.ingest_gdam_snapshot import ingest_gdam_snapshot
from app.etl.ingest_rtm_snapshot import ingest_rtm_snapshot

router = APIRouter(tags=["ingest"])


def _detect_ingest_type(path: Path) -> str:
    xls = pd.ExcelFile(path)
    sheets = set(xls.sheet_names)
    if {"DAM", "GDAM"}.issubset(sheets):
        return "damgdam"
    df = xls.parse(xls.sheet_names[0])
    columns = [str(col).strip().lower() for col in df.columns]
    column_str = "|".join(columns)
    if "weighted" in column_str and "mcp" in column_str:
        return "dam_snapshot"
    if "session" in column_str and "rtm" in path.name.lower():
        return "rtm_snapshot"
    if "gdam" in path.name.lower() or "scheduled" in column_str:
        return "gdam_snapshot"
    if "mcp" in column_str and "session" in column_str:
        return "rtm_snapshot"
    raise ValueError("Unable to detect workbook type")


def _ingest(session: Session, path: Path, ingest_type: str) -> None:
    if ingest_type == "damgdam":
        ingest_damgdam(session, path)
    elif ingest_type == "dam_snapshot":
        ingest_dam_snapshot(session, path)
    elif ingest_type == "gdam_snapshot":
        ingest_gdam_snapshot(session, path)
    elif ingest_type == "rtm_snapshot":
        ingest_rtm_snapshot(session, path)
    else:  # pragma: no cover - defensive
        raise ValueError(f"Unknown ingest type {ingest_type}")


@router.post("/ingest/file")
def ingest_file(upload: UploadFile = File(...), db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(upload.filename or "").suffix) as tmp:
            shutil.copyfileobj(upload.file, tmp)
            tmp_path = Path(tmp.name)
    finally:
        upload.file.close()

    try:
        ingest_type = _detect_ingest_type(tmp_path)
        _ingest(db, tmp_path, ingest_type)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"status": "ok", "type": ingest_type}


@router.post("/ingest/batch")
def ingest_batch(path: str, db: Session = Depends(get_db)) -> dict[str, List[str]]:
    directory = Path(path)
    if not directory.exists() or not directory.is_dir():
        raise HTTPException(status_code=400, detail="Provided path is not a directory")

    processed: List[str] = []
    errors: List[str] = []

    for file_path in sorted(directory.glob("*.xlsx")):
        try:
            ingest_type = _detect_ingest_type(file_path)
            _ingest(db, file_path, ingest_type)
            processed.append(f"{file_path.name}:{ingest_type}")
        except Exception as exc:  # pragma: no cover - logged at API layer
            errors.append(f"{file_path.name}:{exc}")

    return {"processed": processed, "errors": errors}
