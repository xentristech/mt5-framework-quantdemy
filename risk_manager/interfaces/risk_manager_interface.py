# QUANTDEMY - https://quantdemy.com - Trading con Python y MetaTrader 5: Crea tu Propio Framework

from typing import Protocol
from events.events import SizingEvent

class IRiskManager(Protocol):

    def assess_order(self, sizing_event: SizingEvent) -> float | None:
        ...

