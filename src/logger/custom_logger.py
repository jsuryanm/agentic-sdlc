import sys
from datetime import datetime
from loguru import logger

from src.core.config import settings


def _init_logger() -> None:
    """Configure loguru with a fresh logfile per run."""
    logger.remove()  # drop default stderr handler

    # Console handler
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        colorize=True,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[agent]}</cyan> | "
            "<level>{message}</level>"
        ),
    )

    # Per-run file handler — new file every time the process starts
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    logfile = settings.LOG_DIR / f"sdlc_run_{run_ts}.log"

    logger.add(
        str(logfile),
        level=settings.LOG_LEVEL,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{extra[agent]} | {name}:{function}:{line} | {message}"
        ),
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    # Default "agent" tag so non-agent code doesn't break the format
    logger.configure(extra={"agent": "system"})
    logger.info(f"Logger initialized. Logfile: {logfile}")


_init_logger()

__all__ = ["logger"]