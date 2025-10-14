import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from loguru import logger

from .config import get_settings

_LOGGER_INITIALISED = False


def _configure_loguru(log_level: str, log_dir: Optional[Path] = None) -> None:
    logger.remove()
    level = log_level.upper()
    logger.add(lambda msg: logging.getLogger("energyminds").handle(msg), level=level)

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(log_dir / "app.log", maxBytes=10 * 1024 * 1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        file_handler.setFormatter(formatter)
        logging.getLogger("energyminds").addHandler(file_handler)


def configure_logging(log_dir: Optional[str] = None) -> None:
    global _LOGGER_INITIALISED
    if _LOGGER_INITIALISED:
        return

    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    _configure_loguru(settings.log_level, Path(log_dir) if log_dir else None)
    _LOGGER_INITIALISED = True


__all__ = ["configure_logging", "logger"]
