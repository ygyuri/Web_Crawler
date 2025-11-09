"""End-to-end tests for crawler workflow."""

import pytest

from crawler.scraper import BookScraper


@pytest.mark.asyncio
async def test_crawler_crawls_catalog(
    test_db,
    respx_mock,
    sample_catalog_html,
    sample_book_html,
):
    catalog = sample_catalog_html.replace('<li class="next"><a href="page-2.html">next</a></li>', "")
    respx_mock.get(url__regex=r"https://books\.toscrape\.com/+catalogue/page-1\.html").respond(200, text=catalog)
    respx_mock.get(url__regex=r"https://books\.toscrape\.com/+catalogue/book_1/index\.html").respond(200, text=sample_book_html)
    respx_mock.get(url__regex=r"https://books\.toscrape\.com/+catalogue/page-2\.html").respond(404)

    scraper = BookScraper()
    total = await scraper.crawl_all_books(resume=False)
    assert total == 1

    stored = await test_db.books.find_one({"name": "Book One"})
    assert stored is not None

