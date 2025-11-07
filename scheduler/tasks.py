"""Scheduled task definitions."""

import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config.logging_config import get_logger
from config.settings import settings
from scheduler.change_detector import ChangeDetector
from scheduler.reporter import ReportGenerator

logger = get_logger(__name__)


class TaskScheduler:
    """Manages scheduled tasks for crawling and change detection."""

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        # Add daily crawl job
        self.scheduler.add_job(
            self.run_daily_crawl,
            CronTrigger(
                hour=settings.scheduler.crawl_schedule_hour,
                minute=settings.scheduler.crawl_schedule_minute,
                timezone=settings.scheduler.timezone
            ),
            id="daily_crawl",
            name="Daily Book Crawl",
            replace_existing=True
        )

        self.scheduler.start()
        self.is_running = True
        logger.info(
            f"Scheduler started. Daily crawl scheduled for "
            f"{settings.scheduler.crawl_schedule_hour:02d}:"
            f"{settings.scheduler.crawl_schedule_minute:02d} {settings.scheduler.timezone}"
        )

    async def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Scheduler stopped")

    async def run_daily_crawl(self) -> None:
        """
        Run daily crawl and change detection.

        This method is called by the scheduler.
        """
        # Prevent concurrent runs
        if self.lock.locked():
            logger.warning("Daily crawl already running, skipping")
            return

        async with self.lock:
            try:
                logger.info("Starting scheduled daily crawl")

                # Run change detection
                detector = ChangeDetector()
                await detector.initialize()

                try:
                    stats = await detector.detect_changes()
                    logger.info(f"Change detection completed: {stats}")

                    # Generate report
                    reporter = ReportGenerator()
                    await reporter.generate_daily_report(stats)

                finally:
                    await detector.close()

                logger.info("Scheduled daily crawl completed successfully")

            except Exception as e:
                logger.error(f"Scheduled daily crawl failed: {e}", exc_info=True)
                # Send alert if configured
                if settings.scheduler.enable_email_alerts:
                    await self._send_alert(f"Daily crawl failed: {str(e)}")

    async def _send_alert(self, message: str) -> None:
        """
        Send email alert.

        Args:
            message: Alert message
        """
        # TODO: Implement email sending
        logger.warning(f"Alert: {message}")

