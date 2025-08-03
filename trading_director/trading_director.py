# QUANTDEMY - https://quantdemy.com - Trading con Python y MetaTrader 5: Crea tu Propio Framework

from data_provider.data_provider import DataProvider
from signal_generator.interfaces.signal_generator_interface import ISignalGenerator
from position_sizer.position_sizer import PositionSizer
from risk_manager.risk_manager import RiskManager
from order_executor.order_executor import OrderExecutor
from notifications.notifications import NotificationService
from events.events import DataEvent, SignalEvent, SizingEvent, OrderEvent, ExecutionEvent, PlacedPendingOrderEvent
from utils.utils import Utils
from typing import Dict, Callable
import queue
import time


class TradingDirector():
    
    def __init__(self, events_queue: queue.Queue, data_provider: DataProvider, signal_generator: ISignalGenerator,
                position_sizer: PositionSizer, risk_manager: RiskManager, order_executor: OrderExecutor, notification_service: NotificationService):
        """
        Initializes the TradingDirector object.

        Args:
            events_queue (queue.Queue): The queue to receive events.
            data_provider (DataProvider): The data provider object.
            signal_generator (ISignalGenerator): The signal generator object.
            position_sizer (PositionSizer): The position sizer object.
            risk_manager (RiskManager): The risk manager object.
            order_executor (OrderExecutor): The order executor object.
            notification_service (NotificationService): The notification service object.
        """
        self.events_queue = events_queue
        
        # Referencia de los distintos módulos
        self.DATA_PROVIDER = data_provider
        self.SIGNAL_GENERATOR = signal_generator
        self.POSITION_SIZER = position_sizer
        self.RISK_MANAGER = risk_manager
        self.ORDER_EXECUTOR = order_executor
        self.NOTIFICATIONS = notification_service

        # Controlador de trading
        self.continue_trading: bool = True

        # Creación del event handler
        self.event_handler: Dict[str, Callable] = {
            "DATA": self._handle_data_event,
            "SIGNAL": self._handle_signal_event,
            "SIZING": self._handle_sizing_event,
            "ORDER": self._handle_order_event,
            "EXECUTION": self._handle_execution_event,
            "PENDING": self._handle_pending_order_event
        }

    def _handle_data_event(self, event: DataEvent):
        """
        Handle the data event.

        Args:
            event (DataEvent): The data event object.

        Returns:
            None
        """
        # Aquí dentro gestionamos los eventos de tipo DataEvent
        print(f"{Utils.dateprint()} - Recibido DATA EVENT de {event.symbol} - Último precio de cierre: {event.data.close}")
        self.SIGNAL_GENERATOR.generate_signal(event)

    def _handle_signal_event(self, event: SignalEvent):
        """
        Handle the signal event.

        Args:
            event (SignalEvent): The signal event object.

        Returns:
            None
        """
        # Procesamos el signal event
        print(f"{Utils.dateprint()} - Recibido SIGNAL EVENT {event.signal} para {event.symbol}")
        self.POSITION_SIZER.size_signal(event)

    def _handle_sizing_event(self, event: SizingEvent):
        """
        Handle the sizing event.

        Args:
            event (SizingEvent): The sizing event object.

        Returns:
            None
        """
        print(f"{Utils.dateprint()} - Recibido SIZING EVENT con volumen {event.volume} para {event.signal} en {event.symbol}")
        self.RISK_MANAGER.assess_order(event)

    def _handle_order_event(self, event: OrderEvent):
        """
        Handle the order event.

        Args:
            event (OrderEvent): The order event object.

        Returns:
            None
        """
        print(f"{Utils.dateprint()} - Recibido ORDER EVENT con volumen {event.volume} para {event.signal} en {event.symbol}")
        self.ORDER_EXECUTOR.execute_order(event)

    def _handle_execution_event(self, event: ExecutionEvent):
        """
        Handle the execution event.

        Args:
            event (ExecutionEvent): The execution event object.

        Returns:
            None
        """
        print(f"{Utils.dateprint()} - Recibido EXECUTION EVENT {event.signal} en {event.symbol} con volumen {event.volume} al precio {event.fill_price}")
        self._process_execution_or_pending_events(event)

    def _handle_pending_order_event(self, event: PlacedPendingOrderEvent):
        """
        Handle the pending order event.

        Args:
            event (PlacedPendingOrderEvent): The pending order event object.

        Returns:
            None
        """
        print(f"{Utils.dateprint()} - Recibido PLACED PENDING ORDER EVENT con volumen {event.volume} para {event.signal} {event.target_order} en {event.symbol} al precio {event.target_price}")
        self._process_execution_or_pending_events(event)

    def _process_execution_or_pending_events(self, event: ExecutionEvent | PlacedPendingOrderEvent):    # Utilizar el | es para python 3.10 o superior
        """
        Process the execution or pending events.

        Args:
            event (ExecutionEvent | PlacedPendingOrderEvent): The event to be processed.

        Returns:
            None
        """
        if isinstance(event, ExecutionEvent):
            self.NOTIFICATIONS.send_notification(title=f"{event.symbol} - MARKET ORDER", message=f"{Utils.dateprint()} - Ejecutada MARKET ORDER {event.signal} en {event.symbol} con volumen {event.volume} al precio {event.fill_price}")
        elif isinstance(event, PlacedPendingOrderEvent):
            self.NOTIFICATIONS.send_notification(title=f"{event.symbol} - PENDING PLACED", message=f"{Utils.dateprint()} - Colocada PENDING ORDER con volumen {event.volume} para {event.signal} {event.target_order} en {event.symbol} al precio {event.target_price}")
        else:
            pass

    def _handle_none_event(self, event):
        """
        Handles the case when a None event is received.
        
        Prints an error message and sets `continue_trading` flag to False, terminating the execution of the Framework.
        
        Args:
            event: The None event received.
        """
        print(f"{Utils.dateprint()} - ERROR: Recibido evento nulo. Terminando ejecución del Framework")
        self.continue_trading = False

    def _handle_unknown_event(self, event):
        """
        Handles the case when an Unknown event is received.
        
        Prints an error message and sets `continue_trading` flag to False, terminating the execution of the Framework.
        
        Args:
            event: The Unknown event received.
        """
        print(f"{Utils.dateprint()} - ERROR: Recibido evento desconocido. Terminando ejecución del Framework. Evento: {event}")
        self.continue_trading = False

    def execute(self) -> None:
        """
        Executes the main trading loop.

        This method continuously checks for events in the events queue and handles them accordingly.
        If no events are available, it checks for new data from the data provider.
        The loop continues until the `continue_trading` flag is set to False.

        Note:
        - The events are processed by the corresponding event handlers.
        - If an unknown event is encountered, it is handled by the `_handle_unknown_event` method.
        - If a None event is encountered, it is handled by the `_handle_none_event` method.

        Returns:
        None
        """
        # Definición del bucle principal
        while self.continue_trading:
            try:
                event = self.events_queue.get(block=False)    # Recordar que es una cola FIFO
            
            except queue.Empty:
                self.DATA_PROVIDER.check_for_new_data()
            
            else:
                if event is not None:
                    handler = self.event_handler.get(event.event_type, self._handle_unknown_event)
                    handler(event)
                else:
                    self._handle_none_event(event)

            time.sleep(0.01)
        
        print(f"{Utils.dateprint()} - FIN")
