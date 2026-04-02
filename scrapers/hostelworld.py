from __future__ import annotations

import logging
import re
from datetime import date

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from models.hostel import Hostel
from scrapers.base import BaseScraper
from scrapers.selectors import HOSTELWORLD as SEL

logger = logging.getLogger(__name__)

_PLACEHOLDER = "___REPLACE_WITH_ACTUAL_SELECTOR___"


def _is_set(selector: str) -> bool:
    return bool(selector) and selector != _PLACEHOLDER


class HostelworldScraper(BaseScraper):

    def search(self, city: str, checkin: date, checkout: date, max_results: int = 3) -> list[Hostel]:
        hostels: list[Hostel] = []
        try:
            with self.browser() as driver:
                hostels = self._scrape(driver, city, checkin, checkout, max_results)
        except Exception:
            logger.exception("Hostelworld scraper failed for %s", city)
        return hostels

    def search_reuse(self, city: str, checkin: date, checkout: date, max_results: int = 3) -> list[Hostel]:
        try:
            return self._scrape(self.driver, city, checkin, checkout, max_results)
        except Exception:
            logger.exception("Hostelworld reuse search failed for %s", city)
            return []

    def _scrape(
        self, driver, city: str, checkin: date, checkout: date, max_results: int
    ) -> list[Hostel]:
        city_slug = city.lower().replace(" ", "-")
        checkin_str = checkin.strftime("%Y-%m-%d")
        checkout_str = checkout.strftime("%Y-%m-%d")

        url = (
            f"https://www.hostelworld.com/hostels/{city_slug}"
            f"?from={checkin_str}&to={checkout_str}"
            f"&guests=1"
        )
        logger.info("Loading Hostelworld: %s", url)
        driver.get(url)
        self.random_delay(2, 4)

        self.dismiss_cookies(SEL["cookie_accept"])
        self.random_delay(1, 2)

        self._sort_by_price(driver)
        self.random_delay(2, 3)

        cards = self._wait_for_cards(driver)
        if not cards:
            logger.info("No cards on primary URL, trying search URL")
            alt_url = (
                f"https://www.hostelworld.com/st/hostels/s"
                f"?q={city}&from={checkin_str}&to={checkout_str}"
                f"&guests=1"
            )
            driver.get(alt_url)
            self.random_delay(2, 4)
            self.dismiss_cookies(SEL["cookie_accept"])
            self._sort_by_price(driver)
            self.random_delay(1, 2)
            cards = self._wait_for_cards(driver)

        if not cards:
            logger.warning("No hostel cards found for %s", city)
            return []

        logger.info("Found %d hostel cards", len(cards))

        results = self._parse_page(cards, city, max_results)

        if len(results) < max_results:
            more = self._try_next_page(driver, city, max_results - len(results))
            results.extend(more)

        results.sort(key=lambda h: h.price_per_night)
        results = results[:max_results]
        logger.info("Hostelworld: returning %d hostels in %s", len(results), city)
        return results

    def _sort_by_price(self, driver) -> None:
        if not _is_set(SEL.get("sort_button", "")):
            return
        try:
            sort_btn = WebDriverWait(driver, 6).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, SEL["sort_button"]))
            )
            sort_btn.click()
            self.random_delay(0.5, 1.0)

            try:
                price_opt = driver.find_element(
                    By.XPATH,
                    "//button[contains(@class,'item-content') and contains(text(),'Lowest price')]",
                )
                price_opt.click()
            except Exception:
                if _is_set(SEL.get("sort_by_price", "")):
                    try:
                        price_opt = driver.find_element(By.CSS_SELECTOR, SEL["sort_by_price"])
                        price_opt.click()
                    except Exception:
                        logger.debug("Could not click sort-by-price option")
        except Exception:
            logger.debug("Sort button not found or not clickable")

    def _wait_for_cards(self, driver) -> list:
        sel = SEL["hostel_card"]
        if not _is_set(sel):
            logger.warning("hostel_card selector is a placeholder")
            return []
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, sel))
            )
            return driver.find_elements(By.CSS_SELECTOR, sel)
        except Exception:
            return []

    def _try_next_page(self, driver, needed: int, city: str = "") -> list[Hostel]:
        sel = SEL.get("next_page_button", "")
        if not _is_set(sel):
            return []
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            btn.click()
            self.random_delay(2, 4)
            cards = self._wait_for_cards(driver)
            if cards:
                return self._parse_page(cards, city, needed)
        except Exception:
            logger.debug("No next page or pagination click failed")
        return []

    def _parse_page(self, cards: list, city: str, max_results: int) -> list[Hostel]:
        results: list[Hostel] = []
        for i, card in enumerate(cards):
            try:
                hostel = self._parse_card(card, city)
                if hostel:
                    results.append(hostel)
                    if len(results) >= max_results:
                        break
            except Exception:
                logger.debug("Failed to parse hostel card %d", i + 1, exc_info=True)
        return results

    def _parse_card(self, card, city: str) -> Hostel | None:
        name = ""
        if _is_set(SEL["hostel_name"]):
            try:
                el = card.find_element(By.CSS_SELECTOR, ".property-name span")
                name = el.text.strip()
            except Exception:
                pass
        if not name:
            return None

        price = self._extract_dorm_price(card)
        if price is None or price <= 0:
            return None

        rating: float | None = None
        if _is_set(SEL["rating"]):
            try:
                el = card.find_element(By.CSS_SELECTOR, ".score")
                rating = self.safe_float(el.text)
            except Exception:
                pass

        review_count: int | None = None
        if _is_set(SEL["review_count"]):
            try:
                el = card.find_element(By.CSS_SELECTOR, ".num-reviews")
                raw = el.text.strip().strip("()").replace(",", "")
                review_count = int(raw) if raw.isdigit() else None
            except Exception:
                pass

        link = ""
        try:
            link = card.get_attribute("href") or ""
        except Exception:
            pass
        if link and not link.startswith("http"):
            link = f"https://www.hostelworld.com{link}"
        if not link:
            link = "https://www.hostelworld.com"

        return Hostel(
            name=name,
            city=city,
            price_per_night=price,
            rating=rating,
            review_count=review_count,
            booking_link=link,
            source="hostelworld",
        )

    def _extract_dorm_price(self, card) -> float | None:
        try:
            price_elements = card.find_elements(By.CSS_SELECTOR, "strong.current")
        except Exception:
            return None

        if not price_elements:
            return None

        # [0]=Privates, [1]=Dorms — prefer dorms if both exist
        prices: list[float] = []
        for el in price_elements:
            val = self.safe_float(el.text)
            if val is not None and val > 0:
                prices.append(val)

        if not prices:
            return None
        if len(prices) >= 2:
            return prices[1]
        return prices[0]


def search_hostelworld(city: str, checkin: date, checkout: date, max_results: int = 3) -> list[Hostel]:
    return HostelworldScraper().search(city, checkin, checkout, max_results)
