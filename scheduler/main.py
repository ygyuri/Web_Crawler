"""Scheduler service entry point."""

import asyncio
import signal
import sys

from config.logging_config import setup_logging, get_logger
from scheduler.tasks import TaskScheduler

logger = get_logger(__name__)


async def main():
    """Main entry point for scheduler service."""
    setup_logging()
    logger.info("Starting scheduler service")

    scheduler = TaskScheduler()

    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(scheduler.stop())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await scheduler.start()

        # Keep running
        while scheduler.is_running:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Scheduler service failed: {e}", exc_info=True)
        return 1
    finally:
        await scheduler.stop()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

