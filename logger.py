from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    # Keep it simple: just log to stdout.
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def format_log_message(event_type: str, user: str, details: str) -> str:
    return f"{utc_ts()} | {event_type} | {user} | {details}"


async def log_event(
    logger: logging.Logger,
    event_type: str,
    user: str,
    details: str,
    quest_id: Optional[str] = None,
    party_id: Optional[str] = None,
) -> None:
    logger.info(
        "event=%s user=%s quest_id=%s party_id=%s details=%s",
        event_type,
        user,
        quest_id or "",
        party_id or "",
        details,
    )
