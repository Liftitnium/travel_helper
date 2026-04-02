from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.formatter import format_trip_list
from bot.scheduler import daily_scan
from config import DEFAULT_ORIGIN, MAX_RESULTS, SCAN_HOUR, TELEGRAM_BOT_TOKEN
from db.database import get_user, init_db, upsert_user
from models.flight import Flight
from models.hostel import Hostel
from models.trip import Trip
from scrapers.booking import BookingScraper
from scrapers.hostelworld import HostelworldScraper
from scrapers.ryanair import search_ryanair
from scrapers.wizzair import search_wizzair
from utils.cities import get_hostel_city

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)

ASK_ORIGIN, ASK_PRICE = range(2)

WELCOME = (
    "👋 *Welcome to Budget Trip Bot!*\n\n"
    "I find the cheapest weekend trips by combining budget airline fares "
    "(Ryanair & Wizz Air) with the cheapest hostel dorm beds.\n\n"
    "*Commands:*\n"
    "/search — Find cheap trip packages (flights + hostels)\n"
    "/setorigin <IATA> — Set default departure airport\n"
    "/alerts on|off — Toggle daily deal alerts\n"
    "/budget <amount> — Set a max budget filter (€)\n"
    "/help — Show this message\n\n"
    "_Try /search to get started!_"
)

TOP_DESTINATIONS = 5


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await upsert_user(user.id, username=user.username, origin=DEFAULT_ORIGIN)
    await update.message.reply_text(WELCOME, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME, parse_mode="Markdown")


async def cmd_setorigin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /setorigin <IATA code>\nExample: /setorigin BCN")
        return
    code = context.args[0].upper().strip()
    if len(code) != 3 or not code.isalpha():
        await update.message.reply_text("Please provide a valid 3-letter IATA airport code.")
        return
    user = update.effective_user
    await upsert_user(user.id, username=user.username, origin=code)
    await update.message.reply_text(f"✅ Origin airport set to *{code}*.", parse_mode="Markdown")


async def cmd_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Usage: /budget <amount>\nExample: /budget 100\nSet to 0 to remove the cap."
        )
        return
    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")
        return
    user = update.effective_user
    budget_val = amount if amount > 0 else None
    await upsert_user(user.id, username=user.username, budget=budget_val)
    if budget_val:
        await update.message.reply_text(f"✅ Budget cap set to *€{budget_val:.0f}*.", parse_mode="Markdown")
    else:
        await update.message.reply_text("✅ Budget cap removed. Showing all results sorted by price.")


async def cmd_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or context.args[0].lower() not in ("on", "off"):
        await update.message.reply_text("Usage: /alerts on  or  /alerts off")
        return
    enabled = context.args[0].lower() == "on"
    user = update.effective_user
    await upsert_user(user.id, username=user.username, alerts=enabled)
    if enabled:
        await update.message.reply_text(
            f"🔔 Daily alerts *enabled*! I'll message you every morning at {SCAN_HOUR}:00 CET "
            "if there are cheap trips.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("🔕 Daily alerts *disabled*.", parse_mode="Markdown")


async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    user_data = await get_user(user.id)
    saved_origin = user_data["origin"] if user_data else DEFAULT_ORIGIN

    await update.message.reply_text(
        f"What's your origin airport? (3-letter IATA code, e.g. MAD, DUB, STN)\n\n"
        f"_Your saved default is *{saved_origin}* — send that or type a new one._",
        parse_mode="Markdown",
    )
    return ASK_ORIGIN


async def received_origin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().upper()
    if len(text) != 3 or not text.isalpha():
        await update.message.reply_text(
            "That doesn't look like a valid IATA code. Please send a 3-letter airport code (e.g. MAD)."
        )
        return ASK_ORIGIN

    context.user_data["search_origin"] = text

    user = update.effective_user
    await upsert_user(user.id, username=user.username, origin=text)

    await update.message.reply_text(
        "Max price for return flights? (e.g. *50*)\n\n"
        "Or send *any* for no limit.",
        parse_mode="Markdown",
    )
    return ASK_PRICE


async def received_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    origin = context.user_data.get("search_origin", DEFAULT_ORIGIN)

    max_price: float | None = None
    if text not in ("any", "no", "none", "0", ""):
        try:
            max_price = float(text.replace("€", "").replace(",", "."))
        except ValueError:
            await update.message.reply_text(
                "That's not a valid number. Send a price like *50* or *any* for no limit.",
                parse_mode="Markdown",
            )
            return ASK_PRICE

    price_label = f"under €{max_price:.0f}" if max_price else "any price"
    loop = asyncio.get_event_loop()

    await update.message.reply_text(
        f"🟦 Searching *Ryanair* for flights from *{origin}* ({price_label})...",
        parse_mode="Markdown",
    )
    ryanair_flights: list[Flight] = []
    try:
        ryanair_flights = await loop.run_in_executor(
            _executor, search_ryanair, origin, max_price
        )
    except Exception:
        logger.exception("Ryanair search failed for %s", origin)

    if ryanair_flights:
        await update.message.reply_text(
            f"🟦 Ryanair: found *{len(ryanair_flights)}* flights.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("🟦 Ryanair: no flights found.")

    await update.message.reply_text(
        f"🟣 Searching *Wizz Air* for flights from *{origin}* ({price_label})...",
        parse_mode="Markdown",
    )
    wizzair_flights: list[Flight] = []
    try:
        wizzair_flights = await loop.run_in_executor(
            _executor, search_wizzair, origin, max_price
        )
    except Exception:
        logger.exception("Wizz Air search failed for %s", origin)

    if wizzair_flights:
        await update.message.reply_text(
            f"🟣 Wizz Air: found *{len(wizzair_flights)}* flights.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("🟣 Wizz Air: no flights found.")

    all_flights = ryanair_flights + wizzair_flights
    all_flights.sort(key=lambda f: f.price)

    seen: set[str] = set()
    unique_flights: list[Flight] = []
    for flight in all_flights:
        key = flight.destination.upper() if flight.destination else flight.destination_city.lower()
        if key not in seen:
            seen.add(key)
            unique_flights.append(flight)

    top_flights = unique_flights[:TOP_DESTINATIONS]

    if not top_flights:
        reasons = []
        if not ryanair_flights and not wizzair_flights:
            reasons.append("Neither Ryanair nor Wizz Air returned results.")
        if max_price:
            reasons.append(f"Your price cap was €{max_price:.0f} — try a higher limit or send *any*.")
        reasons.append(f"The airport *{origin}* might not have budget routes — try a bigger hub like MAD, STN, or DUB.")

        await update.message.reply_text(
            "😕 *No flights found.*\n\n" + "\n".join(f"• {r}" for r in reasons)
            + "\n\nSend /search to try again.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"✈️ Found flights to *{len(unique_flights)}* destinations. "
        f"Now searching hostels for the *top {len(top_flights)}* cheapest...\n\n"
        "🛏️ This will take a few minutes.",
        parse_mode="Markdown",
    )

    trips: list[Trip] = []
    try:
        trips = await loop.run_in_executor(
            _executor, _hostel_pipeline, top_flights
        )
    except Exception:
        logger.exception("Hostel pipeline crashed")
        await update.message.reply_text(
            "⚠️ Hostel search ran into an error. Showing flight-only results."
        )
        trips = [Trip(flight=f, hostel=None) for f in top_flights]

    with_hostel = sorted([t for t in trips if t.has_hostel], key=lambda t: t.total_cost)
    without_hostel = sorted([t for t in trips if not t.has_hostel], key=lambda t: t.total_cost)
    sorted_trips = (with_hostel + without_hostel)[:MAX_RESULTS]

    hostel_count = len(with_hostel)
    if hostel_count == 0:
        await update.message.reply_text(
            "⚠️ Couldn't find hostels for any destination. Showing flight-only prices."
        )
    elif hostel_count < len(trips):
        missing = len(trips) - hostel_count
        await update.message.reply_text(
            f"ℹ️ Found hostels for *{hostel_count}/{len(trips)}* destinations. "
            f"{missing} shown as flight-only.",
            parse_mode="Markdown",
        )

    message = format_trip_list(sorted_trips, origin)
    await _send_long_message(update, message)
    return ConversationHandler.END


def _hostel_pipeline(flights: list[Flight]) -> list[Trip]:
    trips: list[Trip] = []

    hw = HostelworldScraper()
    hw.open_browser()
    needs_fallback: list[tuple[int, Flight]] = []

    try:
        for i, flight in enumerate(flights):
            city = get_hostel_city(flight)
            logger.info("Hostel search %d/%d — %s", i + 1, len(flights), city)

            hostels: list[Hostel] = []
            try:
                hostels = hw.search_reuse(city, flight.outbound_date, flight.return_date, 1)
            except Exception:
                logger.exception("Hostelworld failed for %s", city)

            if hostels:
                trips.append(Trip(flight=flight, hostel=hostels[0]))
            else:
                trips.append(Trip(flight=flight, hostel=None))
                needs_fallback.append((i, flight))

            if i < len(flights) - 1:
                time.sleep(3)
    finally:
        hw.close_browser()

    if needs_fallback:
        logger.info("Booking.com fallback for %d destinations", len(needs_fallback))
        bk = BookingScraper()
        bk.open_browser()
        try:
            for j, (idx, flight) in enumerate(needs_fallback):
                city = get_hostel_city(flight)
                logger.info("Booking fallback %d/%d — %s", j + 1, len(needs_fallback), city)

                hostels = []
                try:
                    hostels = bk.search_reuse(city, flight.outbound_date, flight.return_date, 1)
                except Exception:
                    logger.exception("Booking.com failed for %s", city)

                if hostels:
                    trips[idx] = Trip(flight=flight, hostel=hostels[0])

                if j < len(needs_fallback) - 1:
                    time.sleep(3)
        finally:
            bk.close_browser()

    return trips


async def _send_long_message(update: Update, message: str) -> None:
    if len(message) > 4000:
        for i in range(0, len(message), 4000):
            await update.message.reply_text(
                message[i : i + 4000],
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
    else:
        await update.message.reply_text(
            message, parse_mode="Markdown", disable_web_page_preview=True
        )


async def search_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Search cancelled. Send /search to start again.")
    return ConversationHandler.END


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set. Create a .env file from .env.example.")
        sys.exit(1)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    search_conv = ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={
            ASK_ORIGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_origin)],
            ASK_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_price)],
        },
        fallbacks=[CommandHandler("cancel", search_cancel)],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("setorigin", cmd_setorigin))
    app.add_handler(CommandHandler("budget", cmd_budget))
    app.add_handler(CommandHandler("alerts", cmd_alerts))
    app.add_handler(search_conv)

    async def on_startup(_app: Application) -> None:
        await init_db()
        scheduler = AsyncIOScheduler(timezone="Europe/Madrid")
        scheduler.add_job(
            daily_scan,
            trigger=CronTrigger(hour=SCAN_HOUR, minute=0),
            id="daily_scan",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Scheduler started — daily scan at %02d:00 CET", SCAN_HOUR)

    app.post_init = on_startup

    logger.info("Bot starting…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
