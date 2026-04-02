from __future__ import annotations

from models.flight import Flight
from models.trip import Trip

AIRLINE_ICON = {
    "Ryanair": "\U0001f7e6",
    "Wizz Air": "\U0001f7e3",
}


def format_flight(flight: Flight, index: int) -> str:
    out_str = flight.outbound_date.strftime("%b %-d")
    ret_str = flight.return_date.strftime("%b %-d")
    nights = flight.nights
    night_label = "night" if nights == 1 else "nights"
    icon = AIRLINE_ICON.get(flight.airline, "✈️")

    lines = [
        f"*{index}. {icon} {flight.airline} → {flight.destination_city}*",
        f"   📅 {out_str} – {ret_str} ({nights} {night_label})",
    ]
    if flight.duration:
        lines.append(f"   ⏱️ {flight.duration}")
    lines.append(f"   💰 €{flight.price:.0f} return")
    lines.append(f"   🔗 [Book]({flight.booking_link})")
    return "\n".join(lines)


def format_flight_list(flights: list[Flight], origin: str) -> str:
    if not flights:
        return (
            f"😕 No cheap flights found from *{origin}* right now.\n"
            "Try again later or search a different airport."
        )

    header = f"✈️ *Found {len(flights)} cheap flights from {origin}:*\n"
    body = "\n\n".join(format_flight(f, i + 1) for i, f in enumerate(flights))
    footer = "\n\n_Prices scraped just now — book fast before they change!_"
    return header + "\n" + body + footer


def format_trip(trip: Trip, index: int) -> str:
    f = trip.flight
    icon = AIRLINE_ICON.get(f.airline, "✈️")
    out_str = f.outbound_date.strftime("%b %-d")
    ret_str = f.return_date.strftime("%b %-d")
    nights = f.nights
    night_label = "night" if nights == 1 else "nights"

    lines = [
        f"*{index}. {f.destination_city}*",
        f"   {icon} {f.airline} — €{f.price:.0f} return",
        f"   📅 {out_str} – {ret_str} ({nights} {night_label})",
    ]

    if trip.has_hostel:
        h = trip.hostel
        rating_str = f" (⭐ {h.rating})" if h.rating else ""
        source = f" — {h.source}" if h.source else ""
        lines.append(
            f"   🛏️ {h.name} — €{h.price_per_night:.0f}/night{rating_str}{source}"
        )
        lines.append(f"   💵 *TOTAL: €{trip.total_cost:.0f}*")
        lines.append(
            f"   🔗 [Flight]({f.booking_link}) · [Hostel]({h.booking_link})"
        )
    else:
        lines.append(f"   🛏️ _No hostel found_")
        lines.append(f"   💵 Flight only: €{trip.total_cost:.0f}")
        lines.append(f"   🔗 [Book flight]({f.booking_link})")

    return "\n".join(lines)


def format_trip_list(trips: list[Trip], origin: str) -> str:
    if not trips:
        return (
            f"😕 No cheap trips found from *{origin}* right now.\n"
            "Try again later or search a different airport."
        )

    header = f"🧳 *Top {len(trips)} cheapest weekend trips from {origin}:*\n"
    separator = "\n\n─────────────────────\n\n"
    body = separator.join(format_trip(t, i + 1) for i, t in enumerate(trips))
    footer = "\n\n_Prices scraped just now — book fast before they change!_"
    return header + "\n" + body + footer


def format_alert_message(
    trips: list[Trip], origin: str, previous_cheapest: float | None
) -> str:
    if not trips:
        return ""

    current = trips[0].total_cost
    header = f"🔔 *Daily deal alert from {origin}!*\n"
    if previous_cheapest:
        diff = previous_cheapest - current
        if diff > 0:
            header += f"📉 Prices dropped €{diff:.0f} since yesterday!\n"

    separator = "\n\n─────────────────────\n\n"
    body = separator.join(format_trip(t, i + 1) for i, t in enumerate(trips[:5]))
    return header + "\n" + body
