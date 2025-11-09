"""Daily report generation."""

import asyncio
import csv
import json
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class ReportGenerator:
    """Generates and optionally emails daily change reports."""

    def __init__(self):
        """Initialize report generator."""
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    async def generate_daily_report(self, stats: Dict) -> None:
        """
        Generate daily change report in JSON and CSV formats and optionally send via email.

        Args:
            stats: Change detection statistics
        """
        try:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            date_dir = self.reports_dir / date_str
            date_dir.mkdir(parents=True, exist_ok=True)

            json_path = date_dir / "changes.json"
            csv_path = date_dir / "changes.csv"

            await asyncio.gather(
                self._generate_json_report(json_path, stats),
                self._generate_csv_report(csv_path, stats)
            )

            logger.info("Daily report generated", extra={"path": str(date_dir)})

            if settings.scheduler.enable_email_alerts:
                await self._send_report_email(date_dir, stats, json_path, csv_path)

        except Exception as exc:
            logger.error("Failed to generate daily report", exc_info=True)
            raise

    async def _generate_json_report(self, path: Path, stats: Dict) -> None:
        """Generate JSON report."""
        report_data = {
            "date": datetime.now(timezone.utc).isoformat(),
            "statistics": stats,
            "summary": {
                "total_processed": stats.get("total_processed", 0),
                "new_books": stats.get("new_books", 0),
                "changed_books": stats.get("changed_books", 0),
                "price_changes": stats.get("price_changes", 0),
                "availability_changes": stats.get("availability_changes", 0),
                "description_changes": stats.get("description_changes", 0),
                "rating_changes": stats.get("rating_changes", 0),
                "errors": stats.get("errors", 0),
            }
        }

        await asyncio.to_thread(self._write_json, path, report_data)

    async def _generate_csv_report(self, path: Path, stats: Dict) -> None:
        """Generate CSV report."""
        rows = [
            ["Metric", "Value"],
            ["Date", datetime.now(timezone.utc).isoformat()],
            ["Total Processed", stats.get("total_processed", 0)],
            ["New Books", stats.get("new_books", 0)],
            ["Changed Books", stats.get("changed_books", 0)],
            ["Unchanged Books", stats.get("unchanged_books", 0)],
            ["Price Changes", stats.get("price_changes", 0)],
            ["Availability Changes", stats.get("availability_changes", 0)],
            ["Description Changes", stats.get("description_changes", 0)],
            ["Rating Changes", stats.get("rating_changes", 0)],
            ["Errors", stats.get("errors", 0)],
        ]

        await asyncio.to_thread(self._write_csv, path, rows)

    @staticmethod
    def _write_json(path: Path, data: Dict) -> None:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

    @staticmethod
    def _write_csv(path: Path, rows: List[List[str]]) -> None:
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerows(rows)

    async def _send_report_email(
        self,
        report_dir: Path,
        stats: Dict,
        json_path: Path,
        csv_path: Path
    ) -> None:
        """Send the daily report via email using configured SMTP settings."""
        if not settings.scheduler.alert_email_to:
            logger.warning("Report email requested but alert recipient is not configured")
            return

        subject_date = report_dir.name
        body = (
            f"Daily crawl report for {subject_date}\n\n"
            f"New books: {stats.get('new_books', 0)}\n"
            f"Changed books: {stats.get('changed_books', 0)}\n"
            f"Price changes: {stats.get('price_changes', 0)}\n"
            f"Availability changes: {stats.get('availability_changes', 0)}\n"
            f"Description changes: {stats.get('description_changes', 0)}\n"
            f"Rating changes: {stats.get('rating_changes', 0)}\n"
            f"Errors: {stats.get('errors', 0)}\n"
        )

        message = EmailMessage()
        message["Subject"] = f"[Crawler] Daily report {subject_date}"
        message["From"] = settings.scheduler.smtp_user or "crawler@localhost"
        message["To"] = settings.scheduler.alert_email_to
        message.set_content(body)

        for attachment in (json_path, csv_path):
            with open(attachment, "rb") as file:
                data = file.read()
                if attachment.suffix == ".json":
                    maintype, subtype = "application", "json"
                else:
                    maintype, subtype = "text", "csv"
                message.add_attachment(
                    data,
                    maintype=maintype,
                    subtype=subtype,
                    filename=attachment.name
                )

        await asyncio.to_thread(self._send_email_message, message)

    @staticmethod
    def _send_email_message(message: EmailMessage) -> None:
        try:
            with smtplib.SMTP(
                settings.scheduler.smtp_host,
                settings.scheduler.smtp_port
            ) as server:
                server.starttls()
                if settings.scheduler.smtp_user and settings.scheduler.smtp_password:
                    server.login(
                        settings.scheduler.smtp_user,
                        settings.scheduler.smtp_password
                    )
                server.send_message(message)
            logger.info(
                "Report email sent",
                extra={"recipient": settings.scheduler.alert_email_to}
            )
        except Exception as exc:
            logger.error(
                "Failed to send report email",
                extra={"error": str(exc)},
                exc_info=True
            )

