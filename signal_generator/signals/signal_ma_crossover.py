# QUANTDEMY - https://quantdemy.com - Trading con Python y MetaTrader 5: Crea tu Propio Framework

from events.events import DataEvent, SignalEvent
from data_provider.data_provider import DataProvider
from ..interfaces.signal_generator_interface import ISignalGenerator
from ..properties.signal_generator_properties import MACrossoverProps
from portfolio.portfolio import Portfolio
from order_executor.order_executor import OrderExecutor

class SignalMACrossover(ISignalGenerator):
    
    def __init__(self, properties: MACrossoverProps):
        """
        Initializes the MACrossover object.

        Args:
            properties (MACrossoverProps): The properties object containing the parameters for the moving average crossover.

        Raises:
            Exception: If the fast period is greater than or equal to the slow period.

        """
        self.timeframe = properties.timeframe
        self.fast_period = properties.fast_period if properties.fast_period > 1 else 2
        self.slow_period = properties.slow_period if properties.slow_period > 2 else 3

        if self.fast_period >= self.slow_period:
            raise Exception(f"ERROR: el periodo rápido ({self.fast_period}) es mayor o igual al periodo lento ({self.slow_period}) para el cálculo de las medias móviles")

    
    def generate_signal(self, data_event: DataEvent, data_provider: DataProvider, portfolio: Portfolio, order_executor: OrderExecutor) -> SignalEvent:
        """
        Generates a signal based on the moving average crossover strategy.

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

        # Recuperamos los datos necesarios para calcular las medias móviles
        bars = data_provider.get_latest_closed_bars(symbol, self.timeframe, self.slow_period)

        # Recuperamos las posiciones abiertas por esta estrategia en el símbolo donde hemos tenido el Data Event
        open_positions = portfolio.get_number_of_strategy_open_positions_by_symbol(symbol)

        # Calculamos el valor de los indicadores
        fast_ma = bars['close'][-self.fast_period:].mean()
        slow_ma = bars['close'].mean()

        # Detectar una señal de compra
        if open_positions['LONG'] == 0 and fast_ma > slow_ma:
            if open_positions['SHORT'] > 0:
                # Tenemos señal de compra, pero tenemos posición de venta. Debemos cerrar la venta ANTES de abrir la compra.
                order_executor.close_strategy_short_positions_by_symbol(symbol)
            signal = "BUY"

        # Señal de venta
        elif open_positions['SHORT'] == 0 and slow_ma > fast_ma:
            if open_positions['LONG'] > 0:
                order_executor.close_strategy_long_positions_by_symbol(symbol)
            signal = "SELL"

        else:
            signal = ""

        # Si tenemos señal, generamos SignalEvent y lo colocamos en la cola de Eventos
        if signal != "":
            signal_event = SignalEvent(symbol=symbol,
                                    signal=signal,
                                    target_order="MARKET",
                                    target_price=0.0,
                                    magic_number=portfolio.magic,
                                    sl=0.0,
                                    tp=0.0)
            
            return signal_event









