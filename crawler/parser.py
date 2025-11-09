"""HTML parsing utilities for extracting book data."""

from dataclasses import dataclass
import re
from typing import List, Optional

from bs4 import BeautifulSoup

from config.logging_config import get_logger
from config.settings import settings
from crawler.models import Book, Rating
from utils.exceptions import ParsingError
from utils.hashing import generate_content_hash
from utils.validators import (
    extract_number,
    extract_price,
    normalize_url,
    sanitize_html,
)

logger = get_logger(__name__)


@dataclass
class CatalogPageSummary:
    """Summary information extracted from a catalog listing page."""

    book_urls: List[str]
    has_next: bool
    current_page: Optional[int]
    total_pages: Optional[int]


class BookParser:
    """Parser for extracting book data from HTML."""

    def __init__(self, base_url: str = None):
        """
        Initialize parser.

        Args:
            base_url: Base URL for normalizing relative URLs.
        """
        self.base_url = base_url or str(settings.crawler.base_url)

    def parse_book_page(self, html: str, url: str) -> Book:
        """
        Parse book data from HTML page.

        Args:
            html: HTML content.
            url: Source URL.

        Returns:
            Book model instance.

        Raises:
            ParsingError: If parsing fails.
        """
        try:
            soup = BeautifulSoup(html, "lxml")

            # Extract all fields with defensive fallbacks.
            name = self._extract_name(soup)
            description = self._extract_description(soup)
            category = self._extract_category(soup)
            price_excl_tax = self._extract_price_excl_tax(soup)
            price_incl_tax = self._extract_price_incl_tax(soup)
            availability = self._extract_availability(soup)
            num_reviews = self._extract_num_reviews(soup)
            image_url = self._extract_image_url(soup)
            rating = self._extract_rating(soup)

            sanitized_html = sanitize_html(html)

            # Create book instance with placeholder hash to satisfy validation
            book = Book(
                name=name,
                description=description,
                category=category,
                price_excl_tax=price_excl_tax,
                price_incl_tax=price_incl_tax,
                availability=availability,
                num_reviews=num_reviews,
                image_url=image_url,
                rating=rating,
                source_url=url,
                raw_html=sanitized_html,
                content_hash="",  # computed after instantiation
            )

            book.content_hash = generate_content_hash(book)
            return book
        except ParsingError:
            raise
        except Exception as exc:
            logger.error(
                "Failed to parse book page",
                extra={"url": url},
                exc_info=True,
            )
            raise ParsingError(f"Failed to parse book page: {exc}") from exc

    def parse_catalog_page(
        self,
        html: str,
        page_url: Optional[str] = None
    ) -> CatalogPageSummary:
        """
        Parse catalog listing page, returning URLs and pagination metadata.

        Args:
            html: HTML content of catalog page.
            page_url: Absolute URL of the catalog page (used for resolving links).

        Returns:
            CatalogPageSummary with book URLs and pagination details.
        """
        try:
            soup = BeautifulSoup(html, "lxml")
            urls = []

            # Find all book articles
            articles = soup.select("article.product_pod")
            for article in articles:
                # Try multiple selectors
                link = (
                    article.select_one("h3 > a") or
                    article.select_one("a") or
                    article.find("a")
                )
                if link and link.get("href"):
                    href = link["href"]
                    # Normalize URL
                    url = self._normalize_catalog_href(href, page_url)
                    urls.append(url)

            # Pagination metadata
            has_next = soup.select_one("li.next > a") is not None
            current_page = None
            total_pages = None
            page_marker = soup.select_one("li.current")
            if page_marker:
                text = page_marker.get_text(strip=True)
                match = re.search(r"Page\s+(\d+)\s+of\s+(\d+)", text, flags=re.IGNORECASE)
                if match:
                    current_page = int(match.group(1))
                    total_pages = int(match.group(2))

            logger.debug(
                "Parsed catalog page",
                extra={
                    "book_count": len(urls),
                    "has_next": has_next,
                    "current_page": current_page,
                    "total_pages": total_pages
                }
            )

            return CatalogPageSummary(
                book_urls=urls,
                has_next=has_next,
                current_page=current_page,
                total_pages=total_pages
            )
        except Exception as exc:
            logger.error("Failed to parse catalog page", exc_info=True)
            raise ParsingError(f"Failed to parse book URLs: {exc}") from exc

    def parse_book_urls(
        self,
        html: str,
        page_url: Optional[str] = None
    ) -> list[str]:
        """
        Extract book URLs from catalog listing page.

        Args:
            html: HTML content of catalog page
            page_url: Absolute URL of the catalog page (used for resolving links)

        Returns:
            List of book URLs
        """
        summary = self.parse_catalog_page(html, page_url=page_url)
        return summary.book_urls

    def has_next_page(self, html: str) -> bool:
        """
        Check if catalog page has a next page.

        Args:
            html: HTML content of catalog page

        Returns:
            True if next page exists
        """
        try:
            soup = BeautifulSoup(html, "lxml")
            next_link = soup.select_one("li.next > a")
            return next_link is not None
        except Exception as e:
            logger.error(f"Failed to check next page: {e}")
            return False

    def _extract_name(self, soup: BeautifulSoup) -> str:
        """Extract book name."""
        # Try multiple selectors
        name_elem = (
            soup.select_one("h1") or
            soup.select_one(".product_main h1") or
            soup.find("h1")
        )
        if name_elem:
            return name_elem.get_text(strip=True)
        raise ParsingError("Could not find book name")

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract book description."""
        # Description is usually after #product_description heading
        desc_heading = soup.select_one("#product_description")
        if desc_heading:
            # Get next sibling paragraph
            next_p = desc_heading.find_next_sibling("p")
            if next_p:
                return next_p.get_text(strip=True)

        # Fallback: try meta description
        meta_desc = soup.select_one('meta[name="description"]')
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"].strip()

        return None

    def _extract_category(self, soup: BeautifulSoup) -> str:
        """Extract book category from breadcrumb."""
        # Breadcrumb: ul.breadcrumb > li:nth-child(3) > a
        breadcrumb_items = soup.select("ul.breadcrumb li")
        if len(breadcrumb_items) >= 3:
            category_link = breadcrumb_items[2].select_one("a")
            if category_link:
                return category_link.get_text(strip=True)

        # Fallback: try to find category elsewhere
        category_elem = soup.select_one(".breadcrumb a")
        if category_elem:
            return category_elem.get_text(strip=True)

        return "Uncategorized"

    def _extract_price_excl_tax(self, soup: BeautifulSoup) -> float:
        """Extract price excluding tax."""
        # Table row with "Price (excl. tax)"
        table_rows = soup.select("table.table tr")
        for row in table_rows:
            th = row.select_one("th")
            if th and "Price (excl. tax)" in th.get_text():
                td = row.select_one("td")
                if td:
                    return extract_price(td.get_text(strip=True))
        return 0.0

    def _extract_price_incl_tax(self, soup: BeautifulSoup) -> float:
        """Extract price including tax."""
        # Table row with "Price (incl. tax)"
        table_rows = soup.select("table.table tr")
        for row in table_rows:
            th = row.select_one("th")
            if th and "Price (incl. tax)" in th.get_text():
                td = row.select_one("td")
                if td:
                    return extract_price(td.get_text(strip=True))

        # Fallback: try price class
        price_elem = soup.select_one(".price_color, .product_price .price_color")
        if price_elem:
            return extract_price(price_elem.get_text(strip=True))

        return 0.0

    def _extract_availability(self, soup: BeautifulSoup) -> str:
        """Extract availability status."""
        # p.availability
        availability_elem = (
            soup.select_one("p.availability") or
            soup.select_one(".availability") or
            soup.find("p", class_="availability")
        )
        if availability_elem:
            return availability_elem.get_text(strip=True)

        # Fallback: check table
        table_rows = soup.select("table.table tr")
        for row in table_rows:
            th = row.select_one("th")
            if th and "Availability" in th.get_text():
                td = row.select_one("td")
                if td:
                    return td.get_text(strip=True)

        return "Unknown"

    def _extract_num_reviews(self, soup: BeautifulSoup) -> int:
        """Extract number of reviews."""
        # Table row with "Number of reviews"
        table_rows = soup.select("table.table tr")
        for row in table_rows:
            th = row.select_one("th")
            if th and "Number of reviews" in th.get_text():
                td = row.select_one("td")
                if td:
                    return extract_number(td.get_text(strip=True))

        return 0

    def _extract_image_url(self, soup: BeautifulSoup) -> str:
        """Extract book cover image URL."""
        # img src in product_gallery or main product image
        img_elem = (
            soup.select_one("#product_gallery img") or
            soup.select_one(".product_main img") or
            soup.select_one("img.thumbnail") or
            soup.select_one("img")
        )
        if img_elem and img_elem.get("src"):
            img_src = img_elem["src"]
            # Handle relative URLs
            return normalize_url(img_src, self.base_url)

        raise ParsingError("Could not find book image URL")

    def _extract_rating(self, soup: BeautifulSoup) -> Rating:
        """Extract book rating from star-rating class."""
        # p.star-rating with class like "star-rating Five"
        rating_elem = (
            soup.select_one("p.star-rating") or
            soup.select_one(".star-rating") or
            soup.find("p", class_=lambda x: x and "star-rating" in x)
        )
        if rating_elem:
            classes = rating_elem.get("class", [])
            if classes:
                try:
                    return Rating.from_star_class(" ".join(classes))
                except ValueError:
                    logger.debug("Unknown rating class", extra={"classes": classes})

        # Fallback: try to find rating in text
        rating_text = soup.get_text()
        for rating in Rating:
            if rating.value in rating_text:
                return rating

        # Default to ONE if not found
        return Rating.ONE

    def _normalize_catalog_href(
        self,
        href: str,
        page_url: Optional[str] = None
    ) -> str:
        """Resolve catalogue link href using the specific page_url when available."""
        base = page_url or self.base_url
        return normalize_url(href, base)

