# QUANTDEMY - https://quantdemy.com - Trading con Python y MetaTrader 5: Crea tu Propio Framework

from events.events import DataEvent, SignalEvent
from data_provider.data_provider import DataProvider
from ..interfaces.signal_generator_interface import ISignalGenerator
from ..properties.signal_generator_properties import RSIProps
from portfolio.portfolio import Portfolio
from order_executor.order_executor import OrderExecutor
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

class SignalRSI(ISignalGenerator):
    
    def __init__(self, properties: RSIProps):
        """
        Initializes the RSI Mean Reversion object.

        Args:
            properties (RSIMeanRev): The properties object containing the parameters for the RSI mean reversion.

        Raises:
            Exception: If the fast period is greater than or equal to the slow period.

        """
        self.timeframe = properties.timeframe
        self.rsi_period = properties.rsi_period if properties.rsi_period > 2 else 2   # Nos aseguramos que el periodo mínimo sea de 2

        if properties.rsi_upper > 100 or properties.rsi_upper < 0:
            self.rsi_upper = 70
        else:
            self.rsi_upper = properties.rsi_upper

        if properties.rsi_lower > 100 or properties.rsi_lower < 0:
            self.rsi_lower = 30
        else:
            self.rsi_lower = properties.rsi_lower
        
        if self.rsi_lower >= self.rsi_upper:
            raise Exception(f"ERROR: el nivel superior ({self.rsi_upper}) es menor o igual al nivel inferior ({self.rsi_lower}) para el cálculo de las señales de entrada")
        
        if properties.sl_points > 0:
            self.sl_points = properties.sl_points
        else:
            self.sl_points = 0

        if properties.tp_points > 0:
            self.tp_points = properties.tp_points
        else:
            self.tp_points = 0
    

    def compute_rsi(self, prices: pd.Series) -> float:

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        average_gain = np.mean(gains[-self.rsi_period:])
        average_loss = np.mean(losses[-self.rsi_period:])

        # Aplicamos formula RSI: RSI = 100 – [100 ÷ ( 1 + (Average Gain During Up Periods ÷ Average Loss During Down Periods ))]
        rs = average_gain / average_loss if average_loss > 0 else 0
        rsi = 100 - (100 / (1 + rs))

        return rsi

    
    def generate_signal(self, data_event: DataEvent, data_provider: DataProvider, portfolio: Portfolio, order_executor: OrderExecutor) -> SignalEvent:
        """
        Generates a signal based on the RSI mean reversion strategy.

        Args:
            data_event (DataEvent): The data event that triggered the signal generation.
            data_provider (DataProvider): The data provider used to retrieve the necessary data.
            portfolio (Portfolio): The portfolio containing the open positions.
            order_executor (OrderExecutor): The order executor used to execute the orders.

        Returns:
            SignalEvent: The generated signal event.
        """
        # Cogemos el símbolo del evento
        symbol = data_event.symbol

        # Recuperamos los datos necesarios para calcular el indicador del RSI
        bars = data_provider.get_latest_closed_bars(symbol, self.timeframe, self.rsi_period + 1)

        # Calculamos el RSI de las últimas velas
        rsi = self.compute_rsi(bars['close'])

        # Recuperamos las posiciones abiertas por esta estrategia en el símbolo donde hemos tenido el Data Event
        open_positions = portfolio.get_number_of_strategy_open_positions_by_symbol(symbol)

        # Detectamos el último precio para calcular SL y TP
        last_tick = data_provider.get_latest_tick(symbol)
        points = mt5.symbol_info(symbol).point

        # Detectar una señal de compra
        if open_positions['LONG'] == 0 and rsi < self.rsi_lower:
            if open_positions['SHORT'] > 0:
                # Tenemos señal de compra, pero tenemos posición de venta. Debemos cerrar la venta ANTES de abrir la compra.
                order_executor.close_strategy_short_positions_by_symbol(symbol)
            signal = "BUY"
            sl = last_tick['ask'] - self.sl_points * points if self.sl_points > 0 else 0
            tp = last_tick['ask'] + self.tp_points * points if self.tp_points > 0 else 0

        # Señal de venta
        elif open_positions['SHORT'] == 0 and rsi > self.rsi_upper:
            if open_positions['LONG'] > 0:
                order_executor.close_strategy_long_positions_by_symbol(symbol)
            signal = "SELL"
            sl = last_tick['bid'] + self.sl_points * points if self.sl_points > 0 else 0
            tp = last_tick['bid'] - self.tp_points * points if self.tp_points > 0 else 0

        else:
            signal = ""

        # Si tenemos señal, generamos SignalEvent y lo colocamos en la cola de Eventos
        if signal != "":
            signal_event = SignalEvent(symbol=symbol,
                                    signal=signal,
                                    target_order="MARKET",
                                    target_price=0.0,
                                    magic_number=portfolio.magic,
                                    sl=sl,
                                    tp=tp)
            
            return signal_event









