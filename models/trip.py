from __future__ import annotations

from dataclasses import dataclass, field

from models.flight import Flight
from models.hostel import Hostel


@dataclass
class Trip:
    flight: Flight
    hostel: Hostel | None = None
    total_cost: float = field(init=False)

    def __post_init__(self) -> None:
        if self.hostel:
            self.total_cost = self.flight.price + (
                self.hostel.price_per_night * self.flight.nights
            )
        else:
            self.total_cost = self.flight.price

    @property
    def has_hostel(self) -> bool:
        return self.hostel is not None

    def __repr__(self) -> str:
        return (
            f"Trip({self.flight.origin}→{self.flight.destination_city} "
            f"€{self.total_cost:.0f} total)"
        )

    def __lt__(self, other: Trip) -> bool:
        return self.total_cost < other.total_cost
