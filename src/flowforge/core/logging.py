from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """Configure application logging with a consistent production-friendly format."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
