"""Entry point for Docker worker service."""

from __future__ import annotations

import asyncio
import os

from anomaly.detector import run_detector_forever, run_detector_realtime
from loguru import logger


async def _main() -> None:
    mode = os.getenv("ANOMALY_DETECTOR_MODE", "poll").strip().lower()
    if mode == "realtime":
        await run_detector_realtime()
    else:
        await run_detector_forever(
            poll_interval_sec=float(os.getenv("ANOMALY_POLL_INTERVAL_SEC", "5"))
        )


if __name__ == "__main__":
    logger.info("Starting anomaly detection worker")
    asyncio.run(_main())
