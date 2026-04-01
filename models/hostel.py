from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Hostel:
    name: str
    city: str
    price_per_night: float
    rating: float | None
    review_count: int | None
    booking_link: str
    source: str  # "hostelworld" or "booking"
    currency: str = "EUR"

    def __repr__(self) -> str:
        star = f"⭐ {self.rating}" if self.rating else "N/A"
        return f"Hostel({self.name} — €{self.price_per_night}/night {star})"
