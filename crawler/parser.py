"""HTML parsing utilities for extracting book data."""

from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from config.logging_config import get_logger
from config.settings import settings
from crawler.models import Book, Rating
from utils.exceptions import ParsingError
from utils.validators import (
    extract_price,
    extract_number,
    normalize_url,
    sanitize_html
)

logger = get_logger(__name__)


class BookParser:
    """Parser for extracting book data from HTML."""

    def __init__(self, base_url: str = None):
        """
        Initialize parser.

        Args:
            base_url: Base URL for normalizing relative URLs
        """
        self.base_url = base_url or str(settings.crawler.base_url)

    def parse_book_page(self, html: str, url: str) -> Book:
        """
        Parse book data from HTML page.

        Args:
            html: HTML content
            url: Source URL

        Returns:
            Book model instance

        Raises:
            ParsingError: If parsing fails
        """
        try:
            soup = BeautifulSoup(html, "lxml")

            # Extract all fields
            name = self._extract_name(soup)
            description = self._extract_description(soup)
            category = self._extract_category(soup)
            price_excl_tax = self._extract_price_excl_tax(soup)
            price_incl_tax = self._extract_price_incl_tax(soup)
            availability = self._extract_availability(soup)
            num_reviews = self._extract_num_reviews(soup)
            image_url = self._extract_image_url(soup, url)
            rating = self._extract_rating(soup)

            # Generate content hash (will be done in scraper with full book object)
            # For now, create a placeholder
            from utils.hashing import generate_content_hash

            # Create book instance
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
                raw_html=sanitize_html(html)
            )

            # Generate content hash
            book.content_hash = generate_content_hash(book)

            return book
        except Exception as e:
            logger.error(f"Failed to parse book page {url}: {e}", exc_info=True)
            raise ParsingError(f"Failed to parse book page: {str(e)}")

    def parse_book_urls(self, html: str) -> list[str]:
        """
        Extract book URLs from catalog listing page.

        Args:
            html: HTML content of catalog page

        Returns:
            List of book URLs
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
                    url = normalize_url(href, self.base_url)
                    urls.append(url)

            logger.debug(f"Extracted {len(urls)} book URLs from catalog page")
            return urls
        except Exception as e:
            logger.error(f"Failed to parse book URLs: {e}", exc_info=True)
            raise ParsingError(f"Failed to parse book URLs: {str(e)}")

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

    def _extract_image_url(self, soup: BeautifulSoup, page_url: str) -> str:
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
            for class_name in classes:
                if "star-rating" in class_name:
                    # Extract rating from class
                    rating_str = class_name.replace("star-rating", "").strip()
                    if rating_str:
                        try:
                            return Rating(rating_str)
                        except ValueError:
                            pass

        # Fallback: try to find rating in text
        rating_text = soup.get_text()
        for rating in Rating:
            if rating.value in rating_text:
                return rating

        # Default to ONE if not found
        return Rating.ONE

