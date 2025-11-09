"""End-to-end tests for scheduler execution."""

import pytest

from scheduler.tasks import TaskScheduler
from scheduler.reporter import ReportGenerator
from database.repositories.change_repository import ChangeRepository


@pytest.mark.asyncio
async def test_scheduler_run_daily_crawl(
    test_db,
    respx_mock,
    sample_catalog_html,
    sample_book_html,
    monkeypatch,
):
    monkeypatch.setattr("config.settings.settings.scheduler.enable_email_alerts", False)

    respx_mock.get(url__regex=r"https://books\.toscrape\.com/+catalogue/page-1\.html").respond(200, text=sample_catalog_html)
    respx_mock.get(url__regex=r"https://books\.toscrape\.com/+catalogue/book_1/index\.html").respond(200, text=sample_book_html)
    respx_mock.get(url__regex=r"https://books\.toscrape\.com/+catalogue/page-2\.html").respond(404)

    reported_stats = {}

    async def fake_generate(self, stats):
        reported_stats.update(stats)

    monkeypatch.setattr(ReportGenerator, "generate_daily_report", fake_generate, raising=False)

    scheduler = TaskScheduler()
    await scheduler.run_daily_crawl()

    assert reported_stats.get("total_processed", 0) >= 1

    change_repo = ChangeRepository(test_db)
    changes = await change_repo.get_recent_changes(limit=10)
    assert len(changes) > 0

