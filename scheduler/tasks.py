"""Scheduled task definitions."""

import asyncio
import smtplib
from email.message import EmailMessage
from typing import Optional
from zoneinfo import ZoneInfo

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

        trigger = CronTrigger(
            hour=settings.scheduler.crawl_schedule_hour,
            minute=settings.scheduler.crawl_schedule_minute,
            timezone=ZoneInfo(settings.scheduler.timezone),
        )

        self.scheduler.add_job(
            self.run_daily_crawl,
            trigger=trigger,
            id="daily_crawl",
            name="Daily Book Crawl",
            replace_existing=True,
            misfire_grace_time=60 * 10,  # 10 minutes grace period
            coalesce=True,
            max_instances=1,
        )

        self.scheduler.start()
        self.is_running = True
        logger.info(
            "Scheduler started",
            extra={
                "hour": settings.scheduler.crawl_schedule_hour,
                "minute": settings.scheduler.crawl_schedule_minute,
                "timezone": settings.scheduler.timezone,
            },
        )

    async def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Scheduler stopped")

    async def run_daily_crawl(self) -> None:
        """
        Run daily crawl and change detection.

        This method is called by the scheduler.
        """
        if self.lock.locked():
            logger.warning("Daily crawl already running, skipping")
            return

        async with self.lock:
            try:
                logger.info("Starting scheduled daily crawl")

                detector = ChangeDetector()
                stats = await detector.detect_changes()
                logger.info("Change detection completed", extra=stats)

                reporter = ReportGenerator()
                await reporter.generate_daily_report(stats)

                logger.info("Scheduled daily crawl completed successfully")

            except Exception as exc:
                logger.error("Scheduled daily crawl failed", exc_info=True)
                if settings.scheduler.enable_email_alerts:
                    await self._send_alert(f"Daily crawl failed: {exc}")

    async def _send_alert(self, message: str) -> None:
        """
        Send email alert.

        Args:
            message: Alert message
        """
        if not settings.scheduler.alert_email_to:
            logger.warning("Alert email requested but no recipient configured")
            return

        email_message = EmailMessage()
        email_message["Subject"] = "[Crawler] Daily crawl alert"
        email_message["From"] = settings.scheduler.smtp_user or "crawler@localhost"
        email_message["To"] = settings.scheduler.alert_email_to
        email_message.set_content(message)

        try:
            if settings.scheduler.smtp_user and settings.scheduler.smtp_password:
                server = smtplib.SMTP(
                    settings.scheduler.smtp_host,
                    settings.scheduler.smtp_port
                )
                server.starttls()
                server.login(
                    settings.scheduler.smtp_user,
                    settings.scheduler.smtp_password
                )
            else:
                server = smtplib.SMTP(
                    settings.scheduler.smtp_host,
                    settings.scheduler.smtp_port
                )

            with server:
                server.send_message(email_message)

            logger.info(
                "Alert email sent",
                extra={"recipient": settings.scheduler.alert_email_to}
            )
        except Exception as exc:
            logger.error(
                "Failed to send alert email",
                extra={"error": str(exc)},
                exc_info=True
            )

