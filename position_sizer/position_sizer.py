# QUANTDEMY - https://quantdemy.com - Trading con Python y MetaTrader 5: Crea tu Propio Framework

from utils.utils import Utils
from data_provider.data_provider import DataProvider
from events.events import SignalEvent, SizingEvent
from .interfaces.position_sizer_interface import IPositionSizer
from .properties.position_sizer_properties import BaseSizerProps, MinSizingProps, FixedSizingProps, RiskPctSizingProps
from .position_sizers.min_size_position_sizer import MinSizePositionSizer
from .position_sizers.fixed_size_position_sizer import FixedSizePositionSizer
from .position_sizers.risk_pct_position_sizer import RiskPctPositionSizer
import MetaTrader5 as mt5
from queue import Queue

class PositionSizer(IPositionSizer):

    def __init__(self, events_queue: Queue, data_provider: DataProvider, sizing_properties: BaseSizerProps):
        """
        Initialize the PositionSizer object.

        Args:
            events_queue (Queue): The queue for receiving events.
            data_provider (DataProvider): The data provider object.
            sizing_properties (BaseSizerProps): The sizing properties object.

        Returns:
            None
        """
        self.events_queue = events_queue
        self.DATA_PROVIDER = data_provider
        self.position_sizing_method = self._get_position_sizing_method(sizing_properties)

    def _get_position_sizing_method(self, sizing_props: BaseSizerProps) -> IPositionSizer:
        """
        Returns the appropriate position sizer based on the given sizing properties.

        Args:
            sizing_props (BaseSizerProps): The sizing properties used to determine the position sizer.

        Returns:
            IPositionSizer: An instance of the appropriate position sizer based on the sizing properties.

        Raises:
            Exception: If the sizing method is unknown or not supported.
        """
        if isinstance(sizing_props, MinSizingProps):
            return MinSizePositionSizer()
        
        elif isinstance(sizing_props, FixedSizingProps):
            return FixedSizePositionSizer(properties=sizing_props)
        
        elif isinstance(sizing_props, RiskPctSizingProps):
            return RiskPctPositionSizer(properties=sizing_props)
        
        else:
            raise Exception(f"ERROR: Método de sizing desconocido: {sizing_props}")

    def _create_and_put_sizing_event(self, signal_event: SignalEvent, volume:float) -> None:
        """
        Creates a sizing event based on the given signal event and volume, and puts it into the events queue.

        Args:
            signal_event (SignalEvent): The signal event to create the sizing event from.
            volume (float): The volume for the sizing event.

        Returns:
            None
        """
        # Creamos el sizing event a partir del signal event y el volume
        sizing_event = SizingEvent(symbol=signal_event.symbol,
                                    signal=signal_event.signal,
                                    target_order=signal_event.target_order,
                                    target_price=signal_event.target_price,
                                    magic_number=signal_event.magic_number,
                                    sl=signal_event.sl,
                                    tp=signal_event.tp,
                                    volume=volume)
        
        # Colocamos el sizing event a la cola de eventos
        self.events_queue.put(sizing_event)

    def size_signal(self, signal_event: SignalEvent) -> None:
        """
        Sizes the position based on the given signal event.

        Args:
            signal_event (SignalEvent): The signal event containing the trading signal.

        Returns:
            None
        """
        # Obtener el volumen adecuado según el método de sizing
        volume = self.position_sizing_method.size_signal(signal_event, self.DATA_PROVIDER)

        # Control de seguridad
        if volume < mt5.symbol_info(signal_event.symbol).volume_min:
            print(f"{Utils.dateprint()} - ERROR: El volumen {volume} es menor al volumen mínimo admitido por el símbolo {signal_event.symbol}")
            return
        
        # Crear el evento y ponerlo en la cola
        self._create_and_put_sizing_event(signal_event, volume)