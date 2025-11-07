"""Daily report generation."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class ReportGenerator:
    """Generates daily change reports."""

    def __init__(self):
        """Initialize report generator."""
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    async def generate_daily_report(self, stats: Dict) -> None:
        """
        Generate daily change report in JSON and CSV formats.

        Args:
            stats: Change detection statistics
        """
        try:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            date_dir = self.reports_dir / date_str
            date_dir.mkdir(parents=True, exist_ok=True)

            # Generate JSON report
            json_path = date_dir / "changes.json"
            await self._generate_json_report(json_path, stats)

            # Generate CSV report
            csv_path = date_dir / "changes.csv"
            await self._generate_csv_report(csv_path, stats)

            logger.info(f"Daily report generated: {date_dir}")

        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}", exc_info=True)
            raise

    async def _generate_json_report(self, path: Path, stats: Dict) -> None:
        """Generate JSON report."""
        report_data = {
            "date": datetime.utcnow().isoformat(),
            "statistics": stats,
            "summary": {
                "total_changes": (
                    stats.get("new_books", 0) +
                    stats.get("changed_books", 0)
                ),
                "new_books": stats.get("new_books", 0),
                "price_changes": stats.get("price_changes", 0),
                "availability_changes": stats.get("availability_changes", 0)
            }
        }

        with open(path, "w") as f:
            json.dump(report_data, f, indent=2)

    async def _generate_csv_report(self, path: Path, stats: Dict) -> None:
        """Generate CSV report."""
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Date", datetime.utcnow().isoformat()])
            writer.writerow(["New Books", stats.get("new_books", 0)])
            writer.writerow(["Changed Books", stats.get("changed_books", 0)])
            writer.writerow(["Price Changes", stats.get("price_changes", 0)])
            writer.writerow(["Availability Changes", stats.get("availability_changes", 0)])
            writer.writerow(["Other Changes", stats.get("other_changes", 0)])

