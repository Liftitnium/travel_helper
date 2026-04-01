from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor

from telegram import Bot

from bot.formatter import format_alert_message
from config import MAX_RESULTS, TELEGRAM_BOT_TOKEN
from db.database import get_alert_users, get_last_cheapest, save_scan_result
from models.trip import Trip
from scrapers.booking import search_booking
from scrapers.hostelworld import search_hostelworld
from scrapers.ryanair import search_ryanair
from scrapers.wizzair import search_wizzair

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)


def _run_pipeline(origin: str, budget: float | None = None) -> list[Trip]:
    """Synchronous pipeline: scrape flights then hostels, assemble trips."""
    logger.info("Pipeline: searching flights from %s", origin)

    flights = []
    try:
        flights.extend(search_ryanair(origin))
    except Exception:
        logger.exception("Ryanair search failed in pipeline")

    try:
        flights.extend(search_wizzair(origin))
    except Exception:
        logger.exception("Wizz Air search failed in pipeline")

    if not flights:
        logger.warning("No flights found from %s", origin)
        return []

    seen: dict[str, object] = {}
    for f in sorted(flights, key=lambda x: x.price):
        key = f.destination_city.lower()
        if key not in seen:
            seen[key] = f
    unique_flights = list(seen.values())

    trips: list[Trip] = []
    for flight in unique_flights:
        city = flight.destination_city
        logger.info("Searching hostels in %s (%s–%s)", city, flight.outbound_date, flight.return_date)

        hostels = []
        try:
            hostels = search_hostelworld(city, flight.outbound_date, flight.return_date)
        except Exception:
            logger.exception("Hostelworld failed for %s", city)

        if not hostels:
            logger.info("Hostelworld empty for %s, trying Booking.com", city)
            try:
                hostels = search_booking(city, flight.outbound_date, flight.return_date)
            except Exception:
                logger.exception("Booking.com failed for %s", city)

        for hostel in hostels:
            trip = Trip(flight=flight, hostel=hostel)
            if budget is None or trip.total_cost <= budget:
                trips.append(trip)

    trips.sort()
    return trips


async def run_pipeline_async(origin: str, budget: float | None = None) -> list[Trip]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _run_pipeline, origin, budget)


async def daily_scan() -> None:
    """Scheduled daily scan for all users with alerts enabled."""
    from db.database import get_alert_users

    logger.info("Starting daily scan")
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    users = await get_alert_users()

    for user in users:
        user_id = user["user_id"]
        origin = user["origin"]
        budget = user.get("budget")

        try:
            trips = await run_pipeline_async(origin, budget)
            if not trips:
                continue

            current_cheapest = trips[0].total_cost
            previous_cheapest = await get_last_cheapest(user_id)

            should_notify = (
                previous_cheapest is None
                or current_cheapest < previous_cheapest
            )

            results_json = json.dumps([
                {
                    "destination": t.flight.destination_city,
                    "total": t.total_cost,
                    "flight_price": t.flight.price,
                    "hostel_price": t.hostel.price_per_night,
                }
                for t in trips[:MAX_RESULTS]
            ])

            await save_scan_result(user_id, current_cheapest, results_json)

            if should_notify:
                message = format_alert_message(trips[:MAX_RESULTS], origin, previous_cheapest)
                if message:
                    await bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode="Markdown",
                        disable_web_page_preview=True,
                    )
                    logger.info("Sent alert to user %d", user_id)
            else:
                logger.info(
                    "No cheaper trips for user %d (current=%.0f, prev=%.0f)",
                    user_id, current_cheapest, previous_cheapest,
                )
        except Exception:
            logger.exception("Daily scan failed for user %d", user_id)

    logger.info("Daily scan complete")
