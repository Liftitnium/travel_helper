from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import DATE_RANGE_WEEKS, TRIP_MAX_NIGHTS, TRIP_MIN_NIGHTS
from models.flight import Flight
from scrapers.base import BaseScraper
from scrapers.selectors import RYANAIR as SEL

logger = logging.getLogger(__name__)

FARE_FINDER_URL = (
    "https://www.ryanair.com/gb/en/fare-finder"
    "?originIata={origin}"
    "&destinationIata=ANY"
    "&isReturn=true"
    "&isMacDestination=false"
    "&promoCode="
    "&adults=1&teens=0&children=0&infants=0"
    "&dateOut={date_out}"
    "&dateIn={date_in}"
)


class RyanairScraper(BaseScraper):
    """Scrape Ryanair fare-finder via URL parameters and extract destination cards."""

    def search(self, origin: str, max_price: float | None = None) -> list[Flight]:
        flights: list[Flight] = []
        try:
            with self.browser() as driver:
                flights = self._scrape(driver, origin, max_price)
        except Exception:
            logger.exception("Ryanair scraper failed")
        return flights

    def _scrape(self, driver, origin: str, max_price: float | None) -> list[Flight]:
        today = date.today()
        end_date = today + timedelta(weeks=DATE_RANGE_WEEKS)
        date_out = today.strftime("%Y-%m-%d")
        date_in = end_date.strftime("%Y-%m-%d")

        url = FARE_FINDER_URL.format(origin=origin, date_out=date_out, date_in=date_in)
        logger.info("Step 1/5 — Loading Ryanair fare finder: %s", url)
        driver.get(url)
        self.random_delay(3, 5)

        logger.info("Step 2/5 — Dismissing cookie consent")
        self.dismiss_cookies(SEL["cookie_accept"])
        self.random_delay(1, 2)

        logger.info("Step 3/5 — Waiting for destination cards to load")
        cards = self._wait_for_cards(driver)
        if not cards:
            logger.warning("No destination cards found on Ryanair fare finder")
            return []
        logger.info("Found %d destination cards initially", len(cards))

        logger.info("Step 4/5 — Scrolling to load all destinations")
        cards = self._scroll_and_collect(driver)
        logger.info("Total destination cards after scrolling: %d", len(cards))

        logger.info("Step 5/5 — Parsing %d destination cards", len(cards))
        results: list[Flight] = []
        for i, card in enumerate(cards):
            try:
                flight = self._parse_card(card, origin)
                if flight is None:
                    continue
                if flight.nights < TRIP_MIN_NIGHTS or flight.nights > TRIP_MAX_NIGHTS:
                    logger.debug(
                        "Skipping %s — %d nights (outside %d–%d range)",
                        flight.destination_city, flight.nights, TRIP_MIN_NIGHTS, TRIP_MAX_NIGHTS,
                    )
                    continue
                if max_price is not None and flight.price > max_price:
                    logger.debug("Skipping %s — €%.0f exceeds max €%.0f", flight.destination_city, flight.price, max_price)
                    continue
                results.append(flight)
                logger.debug("Parsed card %d: %s", i + 1, flight)
            except Exception:
                logger.debug("Failed to parse card %d", i + 1, exc_info=True)

        results.sort(key=lambda f: f.price)
        logger.info("Ryanair: returning %d flights from %s", len(results), origin)
        return results

    def _wait_for_cards(self, driver) -> list:
        sel = SEL["destination_card"]
        if sel == "___REPLACE_WITH_ACTUAL_SELECTOR___":
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
            logger.warning("Timed out waiting for destination cards (selector: %s)", sel)
            return []

    def _scroll_and_collect(self, driver) -> list:
        """Scroll the results list to trigger lazy-loading until no new cards appear."""
        sel = SEL["destination_card"]
        if sel == "___REPLACE_WITH_ACTUAL_SELECTOR___":
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

    def _parse_card(self, card, origin: str) -> Flight | None:
        # The card is a <button data-iata-code="ESU" data-ref="RESULT_ESU_2026-04-10_2026-04-17">
        iata_code = card.get_attribute("data-iata-code") or ""
        data_ref = card.get_attribute("data-ref") or ""

        if not iata_code:
            logger.debug("Card missing data-iata-code attribute")
            return None

        city = self._extract_text(card, SEL["city_name"])
        duration = self._extract_text(card, SEL["duration"])
        price_text = self._extract_text(card, SEL["price"])

        if not city:
            logger.debug("No city name found in card for %s", iata_code)
            return None

        price = self.safe_float(price_text) if price_text else None
        if price is None or price <= 0:
            logger.debug("No valid price for %s (raw: %r)", city, price_text)
            return None

        outbound, return_d = self._parse_data_ref(data_ref)
        if outbound is None or return_d is None:
            dates_text = self._extract_text(card, SEL["dates"])
            outbound, return_d = self._parse_dates(dates_text)
        if outbound is None or return_d is None:
            logger.debug("Could not parse dates for %s (data-ref: %r)", city, data_ref)
            return None

        booking_link = (
            f"https://www.ryanair.com/gb/en/trip/flights/select"
            f"?origin={origin}&destination={iata_code}"
            f"&dateOut={outbound.strftime('%Y-%m-%d')}"
            f"&dateIn={return_d.strftime('%Y-%m-%d')}"
            f"&adults=1"
        )

        return Flight(
            origin=origin,
            destination=iata_code,
            destination_city=city,
            outbound_date=outbound,
            return_date=return_d,
            price=price,
            airline="Ryanair",
            booking_link=booking_link,
            duration=duration or "",
        )

    def _extract_text(self, card, selector: str) -> str:
        if not selector or selector == "___REPLACE_WITH_ACTUAL_SELECTOR___":
            return ""
        try:
            el = card.find_element(By.CSS_SELECTOR, selector)
            return el.text.strip()
        except Exception:
            return ""

    @staticmethod
    def _parse_data_ref(data_ref: str) -> tuple[date | None, date | None]:
        """Parse 'RESULT_ESU_2026-04-10_2026-04-17' into (outbound, return) dates."""
        if not data_ref:
            return None, None
        match = re.match(
            r"RESULT_[A-Z]{3}_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})",
            data_ref,
        )
        if not match:
            return None, None
        try:
            out = datetime.strptime(match.group(1), "%Y-%m-%d").date()
            ret = datetime.strptime(match.group(2), "%Y-%m-%d").date()
            return out, ret
        except ValueError:
            return None, None

    @staticmethod
    def _parse_dates(text: str) -> tuple[date | None, date | None]:
        """Parse date range like 'Apr 9 - 16' or 'Apr 9 - May 2' into (outbound, return)."""
        if not text:
            return None, None

        current_year = date.today().year

        full_range = re.match(
            r"([A-Za-z]+)\s+(\d{1,2})\s*[-–]\s*([A-Za-z]+)\s+(\d{1,2})",
            text.strip(),
        )
        if full_range:
            try:
                out = datetime.strptime(f"{full_range.group(1)} {full_range.group(2)} {current_year}", "%b %d %Y").date()
                ret = datetime.strptime(f"{full_range.group(3)} {full_range.group(4)} {current_year}", "%b %d %Y").date()
                if ret < out:
                    ret = ret.replace(year=current_year + 1)
                return out, ret
            except ValueError:
                pass

        same_month = re.match(
            r"([A-Za-z]+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2})",
            text.strip(),
        )
        if same_month:
            try:
                month_str = same_month.group(1)
                day_out = int(same_month.group(2))
                day_in = int(same_month.group(3))
                out = datetime.strptime(f"{month_str} {day_out} {current_year}", "%b %d %Y").date()
                ret = datetime.strptime(f"{month_str} {day_in} {current_year}", "%b %d %Y").date()
                if ret < out:
                    ret = ret.replace(year=current_year + 1)
                return out, ret
            except ValueError:
                pass

        return None, None


def search_ryanair(origin: str, max_price: float | None = None) -> list[Flight]:
    return RyanairScraper().search(origin, max_price)
