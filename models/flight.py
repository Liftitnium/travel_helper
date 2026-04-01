from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Flight:
    origin: str
    destination: str
    destination_city: str
    outbound_date: date
    return_date: date
    price: float
    airline: str
    booking_link: str
    duration: str = ""
    currency: str = "EUR"
    nights: int = field(init=False)

    def __post_init__(self) -> None:
        self.nights = (self.return_date - self.outbound_date).days

    def __repr__(self) -> str:
        return (
            f"Flight({self.origin}→{self.destination} "
            f"{self.outbound_date}–{self.return_date} "
            f"€{self.price} {self.airline})"
        )
