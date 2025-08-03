# QUANTDEMY - https://quantdemy.com - Trading con Python y MetaTrader 5: Crea tu Propio Framework

from typing import Protocol

class INotificationChannel(Protocol):
    
    def send_message(self, title: str, message: str):
        ...