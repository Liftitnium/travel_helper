from __future__ import annotations

import calendar
import logging
import re
from datetime import date, timedelta

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import DATE_RANGE_WEEKS, TRIP_MAX_NIGHTS, TRIP_MIN_NIGHTS
from models.flight import Flight
from scrapers.base import BaseScraper
from scrapers.selectors import WIZZAIR as SEL

logger = logging.getLogger(__name__)

FARE_FINDER_URL = "https://wizzair.com/en-gb/flights/fare-finder"

_PLACEHOLDER = "___REPLACE_WITH_ACTUAL_SELECTOR___"


def _is_set(selector: str) -> bool:
    return bool(selector) and selector != _PLACEHOLDER


class WizzairScraper(BaseScraper):
    """Scrape Wizz Air fare-finder by interacting with the search form."""

    def search(self, origin: str, max_price: float | None = None) -> list[Flight]:
        flights: list[Flight] = []
        try:
            with self.browser() as driver:
                flights = self._scrape(driver, origin, max_price)
        except Exception:
            logger.exception("Wizz Air scraper failed")
        return flights

    # ── Main pipeline ────────────────────────────────────────────────────────

    def _scrape(self, driver, origin: str, max_price: float | None) -> list[Flight]:
        logger.info("Step 1/7 — Loading Wizz Air fare finder: %s", FARE_FINDER_URL)
        driver.get(FARE_FINDER_URL)
        self.random_delay(3, 6)

        logger.info("Step 2/7 — Dismissing cookie consent")
        self.dismiss_cookies(SEL["cookie_accept"])
        self.random_delay(1, 2)

        logger.info("Step 3/7 — Selecting 'Return' trip type")
        self._select_return_trip(driver)
        self.random_delay(1, 2)

        logger.info("Step 4/7 — Entering origin airport: %s", origin)
        self._enter_origin(driver, origin)
        self.random_delay(1, 3)

        logger.info("Step 5/7 — Clicking Search")
        self._click_search(driver)
        self.random_delay(3, 5)

        logger.info("Step 6/7 — Waiting for destination cards to load")
        cards = self._wait_for_cards(driver)
        if not cards:
            logger.warning("No destination cards found on Wizz Air fare finder")
            return []
        logger.info("Found %d destination cards initially", len(cards))

        cards = self._scroll_and_collect(driver)
        logger.info("Total destination cards after scrolling: %d", len(cards))

        logger.info("Step 7/7 — Parsing %d destination cards", len(cards))
        results: list[Flight] = []
        for i, card in enumerate(cards):
            try:
                flight = self._parse_card(card, origin)
                if flight is None:
                    continue
                if max_price is not None and flight.price > max_price:
                    logger.debug(
                        "Skipping %s — €%.0f exceeds max €%.0f",
                        flight.destination_city, flight.price, max_price,
                    )
                    continue
                results.append(flight)
                logger.debug("Parsed card %d: %s", i + 1, flight)
            except Exception:
                logger.debug("Failed to parse card %d", i + 1, exc_info=True)

        results.sort(key=lambda f: f.price)
        logger.info("Wizz Air: returning %d flights from %s", len(results), origin)
        return results

    # ── Form interaction ─────────────────────────────────────────────────────

    def _select_return_trip(self, driver) -> None:
        """Click the Return radio toggle. It's a radio <input> — use JS click or the wrapping <label>."""
        if not _is_set(SEL["return_trip_toggle"]):
            logger.warning("return_trip_toggle selector is a placeholder — skipping")
            return
        try:
            toggle = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, SEL["return_trip_toggle"]))
            )
            driver.execute_script("arguments[0].click();", toggle)
            logger.info("Clicked 'Return' trip type toggle via JS")
        except Exception:
            logger.warning("Could not click Return trip toggle", exc_info=True)

    def _enter_origin(self, driver, origin: str) -> None:
        if not _is_set(SEL["origin_input"]):
            logger.warning("origin_input selector is a placeholder — skipping")
            return
        try:
            inp = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, SEL["origin_input"]))
            )
            inp.click()
            self.random_delay(0.3, 0.6)

            inp.send_keys(Keys.CONTROL + "a")
            inp.send_keys(Keys.DELETE)
            self.random_delay(0.2, 0.4)

            logger.info("Typing origin '%s' character by character", origin)
            self.human_type(inp, origin)
            self.random_delay(1, 2)

            # Click the exact matching dropdown item: label[data-test="MAD"]
            dropdown_sel = f'label[data-test="{origin}"]'
            logger.info("Waiting for dropdown suggestion: %s", dropdown_sel)
            try:
                suggestion = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, dropdown_sel))
                )
                suggestion.click()
                logger.info("Clicked origin dropdown suggestion for %s", origin)
            except Exception:
                logger.warning(
                    "Exact dropdown match not found for %s — trying first generic suggestion",
                    origin,
                )
                if _is_set(SEL["origin_dropdown_item"]):
                    try:
                        fallback = WebDriverWait(driver, 4).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, SEL["origin_dropdown_item"]))
                        )
                        fallback.click()
                        logger.info("Clicked first generic dropdown suggestion")
                    except Exception:
                        logger.warning("No dropdown suggestion appeared — pressing Enter")
                        inp.send_keys(Keys.ENTER)
                else:
                    inp.send_keys(Keys.ENTER)

        except Exception:
            logger.warning("Could not enter origin airport", exc_info=True)

    def _click_search(self, driver) -> None:
        if not _is_set(SEL["search_button"]):
            logger.warning("search_button selector is a placeholder — skipping")
            return
        try:
            btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, SEL["search_button"]))
            )
            btn.click()
            logger.info("Clicked search button")
        except Exception:
            logger.warning("Could not click search button", exc_info=True)

    # ── Results loading ──────────────────────────────────────────────────────

    def _wait_for_cards(self, driver) -> list:
        sel = SEL["destination_card"]
        if not _is_set(sel):
            logger.warning(
                "destination_card selector is still a placeholder! "
                "Open scrapers/selectors.py and paste the real CSS selector."
            )
            return []
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, sel))
            )
            return driver.find_elements(By.CSS_SELECTOR, sel)
        except Exception:
            logger.warning("Timed out waiting for Wizz Air destination cards (selector: %s)", sel)
            return []

    def _scroll_and_collect(self, driver) -> list:
        sel = SEL["destination_card"]
        if not _is_set(sel):
            return []

        previous_count = 0
        stable_rounds = 0
        max_scrolls = 15

        for i in range(max_scrolls):
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            current_count = len(cards)
            logger.debug("Scroll %d — %d cards loaded", i + 1, current_count)

            if current_count == previous_count:
                stable_rounds += 1
                if stable_rounds >= 2:
                    logger.debug("No new cards after %d stable scrolls, stopping", stable_rounds)
                    break
            else:
                stable_rounds = 0

            previous_count = current_count

            if cards:
                driver.execute_script("arguments[0].scrollIntoView(false);", cards[-1])
            else:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")

            self.random_delay(1.5, 3.0)

        return driver.find_elements(By.CSS_SELECTOR, sel)

    # ── Card parsing ─────────────────────────────────────────────────────────

    def _parse_card(self, card, origin: str) -> Flight | None:
        # ── City name + IATA code from <p data-test="{IATA}">CityName</p> ──
        city = ""
        dest_iata = ""
        try:
            city_el = card.find_element(By.CSS_SELECTOR, SEL["city_name"])
            city = city_el.text.strip()
            dest_iata = (city_el.get_attribute("data-test") or "").strip()
        except Exception:
            logger.debug("Could not find city element in card")

        if not city:
            logger.debug("No city name found in Wizz Air card")
            return None
        if not dest_iata:
            dest_iata = city[:3].upper()

        # ── Price from data-test attribute: "amount-39.98-currency-EUR" ──────
        price: float | None = None
        try:
            price_el = card.find_element(By.CSS_SELECTOR, SEL["price"])
            data_test = price_el.get_attribute("data-test") or ""
            parts = data_test.split("-")
            # "amount", "39.98", "currency", "EUR"
            if len(parts) >= 2:
                price = float(parts[1])
        except Exception:
            logger.debug("Could not extract price from data-test for %s", city)

        if price is None or price <= 0:
            logger.debug("No valid price for %s", city)
            return None

        # ── Dates from offer-month: "in April" or "in April - May" ───────────
        dates_text = ""
        try:
            dates_el = card.find_element(By.CSS_SELECTOR, SEL["dates"])
            dates_text = dates_el.text.strip()
        except Exception:
            pass

        outbound, return_d = self._estimate_dates_from_month(dates_text)

        # ── Duration ─────────────────────────────────────────────────────────
        duration = ""
        try:
            dur_el = card.find_element(By.CSS_SELECTOR, SEL["duration"])
            duration = dur_el.text.strip()
        except Exception:
            pass

        # ── Booking link (general fare finder link since dates are approximate)
        booking_link = f"https://wizzair.com/en-gb/flights/fare-finder#{origin}-{dest_iata}"

        return Flight(
            origin=origin,
            destination=dest_iata,
            destination_city=city,
            outbound_date=outbound,
            return_date=return_d,
            price=price,
            airline="Wizz Air",
            booking_link=booking_link,
            duration=duration,
        )

    # ── Date helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _estimate_dates_from_month(text: str) -> tuple[date, date]:
        """Turn 'in April' or 'in April - May' into an approximate (outbound, return) pair.

        Uses the first Friday of the named month as outbound, +2 days for a weekend trip.
        Falls back to the next upcoming Friday if parsing fails.
        """
        today = date.today()

        month_names = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
        month_abbrs = {m.lower(): i for i, m in enumerate(calendar.month_abbr) if m}
        all_months = {**month_names, **month_abbrs}

        cleaned = re.sub(r"^in\s+", "", text.strip(), flags=re.IGNORECASE)
        # Take the first month mentioned (e.g., "April" from "April - May")
        first_part = re.split(r"\s*[-–]\s*", cleaned)[0].strip().lower()

        month_num = all_months.get(first_part)
        if month_num is None:
            # Fallback: next Friday from today
            days_ahead = (4 - today.weekday()) % 7 or 7
            outbound = today + timedelta(days=days_ahead)
            return outbound, outbound + timedelta(days=2)

        year = today.year
        first_of_month = date(year, month_num, 1)
        if first_of_month < today:
            first_of_month = date(year + 1, month_num, 1)

        # Find the first Friday in that month
        days_until_friday = (4 - first_of_month.weekday()) % 7
        outbound = first_of_month + timedelta(days=days_until_friday)

        return outbound, outbound + timedelta(days=2)


def search_wizzair(origin: str, max_price: float | None = None) -> list[Flight]:
    return WizzairScraper().search(origin, max_price)
