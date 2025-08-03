# QUANTDEMY - https://quantdemy.com - Trading con Python y MetaTrader 5: Crea tu Propio Framework

from events.events import DataEvent
from .interfaces.signal_generator_interface import ISignalGenerator
from .properties.signal_generator_properties import BaseSignalProps, MACrossoverProps, RSIProps
from .signals.signal_ma_crossover import SignalMACrossover
from .signals.signal_rsi_mr import SignalRSI
from data_provider.data_provider import DataProvider
from portfolio.portfolio import Portfolio
from order_executor.order_executor import OrderExecutor
from queue import Queue

class SignalGenerator(ISignalGenerator):

    def __init__(self, events_queue: Queue, data_provider: DataProvider, portfolio: Portfolio, order_executor: OrderExecutor, signal_properties: BaseSignalProps):
        """
        Initialize the SignalGenerator object.

        Args:
            events_queue (Queue): The queue for receiving events.
            data_provider (DataProvider): The data provider for accessing market data.
            portfolio (Portfolio): The portfolio for managing positions and balances.
            order_executor (OrderExecutor): The order executor for executing trading orders.
            signal_properties (BaseSignalProps): The signal properties for generating trading signals.
        """
        self.events_queue = events_queue
        self.DATA_PROVIDER = data_provider
        self.PORTFOLIO = portfolio
        self.ORDER_EXECUTOR = order_executor

        self.signal_generator_method = self._get_signal_generator_method(signal_properties)

    def _get_signal_generator_method(self, signal_props: BaseSignalProps) -> ISignalGenerator:
        """
        Returns an instance of ISignalGenerator based on the provided signal properties.

        Args:
            signal_props (BaseSignalProps): The signal properties used to determine the type of signal generator.

        Returns:
            ISignalGenerator: An instance of ISignalGenerator.

        Raises:
            Exception: If the signal properties are of an unknown type.
        """
        if isinstance(signal_props, MACrossoverProps):
            return SignalMACrossover(properties=signal_props)
        
        elif isinstance(signal_props, RSIProps):
            return SignalRSI(properties=signal_props)
        
        else:
            raise Exception(f"ERROR: Método de sizing desconocido: {signal_props}")

    def generate_signal(self, data_event: DataEvent) -> None:
        """
        Generates a signal based on the given data event.

        Args:
            data_event (DataEvent): The data event used to generate the signal.

        Returns:
            None
        """
        # Recuperamos el SignalEvent usando la lógica de entrada adecuada
        signal_event = self.signal_generator_method.generate_signal(data_event, self.DATA_PROVIDER, self.PORTFOLIO, self.ORDER_EXECUTOR)

        # Comprobamos que SignalEvent no sea None y colocamos el evento a la cola
        if signal_event is not None:
            self.events_queue.put(signal_event)