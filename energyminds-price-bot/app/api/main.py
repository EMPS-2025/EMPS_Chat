from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging

from .routers import health, ingest, prices

configure_logging()
settings = get_settings()

app = FastAPI(title="EnergyMinds Price Bot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(prices.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok"}
