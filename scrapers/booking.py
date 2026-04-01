from __future__ import annotations

import logging
import re
from datetime import date

from selenium.webdriver.common.by import By

from models.hostel import Hostel
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class BookingScraper(BaseScraper):
    """Fallback scraper: Booking.com filtered to hostels."""

    def search(self, city: str, checkin: date, checkout: date, max_results: int = 3) -> list[Hostel]:
        """Single search — opens and closes its own browser."""
        hostels: list[Hostel] = []
        try:
            with self.browser() as driver:
                hostels = self._scrape(driver, city, checkin, checkout, max_results)
        except Exception:
            logger.exception("Booking.com scraper failed for %s", city)
        return hostels

    def search_reuse(self, city: str, checkin: date, checkout: date, max_results: int = 3) -> list[Hostel]:
        """Search using an already-open browser. Call open_browser() first, close_browser() when done."""
        try:
            return self._scrape(self.driver, city, checkin, checkout, max_results)
        except Exception:
            logger.exception("Booking.com reuse search failed for %s", city)
            return []

    def _scrape(self, driver, city: str, checkin: date, checkout: date, max_results: int) -> list[Hostel]:
        checkin_str = checkin.strftime("%Y-%m-%d")
        checkout_str = checkout.strftime("%Y-%m-%d")

        url = (
            f"https://www.booking.com/searchresults.html"
            f"?ss={city.replace(' ', '+')}"
            f"&checkin={checkin_str}"
            f"&checkout={checkout_str}"
            f"&group_adults=1&no_rooms=1"
            f"&nflt=ht_id%3D203"  # 203 = hostel property type
            f"&order=price"
        )

        logger.info("Loading Booking.com: %s", url)
        driver.get(url)
        self.random_delay(3, 6)
        self.dismiss_cookies()
        self.random_delay(1, 3)

        return self._parse_results(driver, city, max_results)

    def _parse_results(self, driver, city: str, max_results: int) -> list[Hostel]:
        results: list[Hostel] = []

        card_selectors = [
            "[data-testid='property-card']",
            ".sr_property_block",
            "[class*='property-card']",
            "[class*='PropertyCard']",
            ".js-sr-card",
        ]

        cards = []
        for sel in card_selectors:
            try:
                cards = self.wait_and_find_all(By.CSS_SELECTOR, sel, timeout=12)
                if cards:
                    break
            except Exception:
                continue

        if not cards:
            logger.warning("Booking.com: no property cards found for %s", city)
            return self._fallback_parse(driver, city, max_results)

        for card in cards[:max_results * 2]:
            try:
                hostel = self._parse_card(card, city)
                if hostel:
                    results.append(hostel)
                    if len(results) >= max_results:
                        break
            except Exception:
                logger.debug("Failed to parse Booking.com card", exc_info=True)

        results.sort(key=lambda h: h.price_per_night)
        return results[:max_results]

    def _parse_card(self, card, city: str) -> Hostel | None:
        text = card.text
        if not text:
            return None

        name = ""
        for sel in [
            "[data-testid='title']", ".sr-hotel__name", "[class*='title']",
            "h3", "h2", "[class*='name']",
        ]:
            try:
                el = card.find_element(By.CSS_SELECTOR, sel)
                name = el.text.strip()
                if name:
                    break
            except Exception:
                continue

        price: float | None = None
        for sel in [
            "[data-testid='price-and-discounted-price']",
            ".bui-price-display__value",
            "[class*='price']",
            "[class*='Price']",
            "span[class*='price']",
        ]:
            try:
                el = card.find_element(By.CSS_SELECTOR, sel)
                price = self.safe_float(el.text)
                if price and price > 0:
                    break
            except Exception:
                continue

        if price is None:
            price_match = re.search(r"[€$£]\s*(\d+[.,]?\d*)", text)
            if price_match:
                price = float(price_match.group(1).replace(",", "."))

        if not name or not price or price <= 0:
            return None

        rating: float | None = None
        for sel in [
            "[data-testid='review-score']", ".bui-review-score__badge",
            "[class*='review-score']", "[class*='rating']",
        ]:
            try:
                el = card.find_element(By.CSS_SELECTOR, sel)
                rating = self.safe_float(el.text)
                if rating:
                    break
            except Exception:
                continue

        review_count: int | None = None
        review_match = re.search(r"(\d[\d,]*)\s*review", text, re.IGNORECASE)
        if review_match:
            review_count = int(review_match.group(1).replace(",", ""))

        link = ""
        try:
            link_el = card.find_element(By.CSS_SELECTOR, "a[href*='booking.com']")
            link = link_el.get_attribute("href") or ""
        except Exception:
            try:
                link_el = card.find_element(By.TAG_NAME, "a")
                link = link_el.get_attribute("href") or ""
            except Exception:
                pass

        if not link.startswith("http"):
            link = f"https://www.booking.com{link}" if link else "https://www.booking.com"

        return Hostel(
            name=name,
            city=city,
            price_per_night=price,
            rating=rating,
            review_count=review_count,
            booking_link=link,
            source="booking",
        )

    def _fallback_parse(self, driver, city: str, max_results: int) -> list[Hostel]:
        results: list[Hostel] = []
        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            blocks = re.split(r"\n{2,}", body)
            for block in blocks:
                price_match = re.search(r"[€$£]\s*(\d+[.,]?\d*)", block)
                if not price_match:
                    continue
                price = float(price_match.group(1).replace(",", "."))
                lines = [l.strip() for l in block.split("\n") if l.strip()]
                name = lines[0] if lines else "Unknown Hostel"

                results.append(Hostel(
                    name=name,
                    city=city,
                    price_per_night=price,
                    rating=None,
                    review_count=None,
                    booking_link="https://www.booking.com",
                    source="booking",
                ))
                if len(results) >= max_results:
                    break
        except Exception:
            logger.debug("Booking.com fallback parse failed", exc_info=True)
        return results


def search_booking(city: str, checkin: date, checkout: date, max_results: int = 3) -> list[Hostel]:
    return BookingScraper().search(city, checkin, checkout, max_results)
