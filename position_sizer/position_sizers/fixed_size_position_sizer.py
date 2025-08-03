# QUANTDEMY - https://quantdemy.com - Trading con Python y MetaTrader 5: Crea tu Propio Framework

from data_provider.data_provider import DataProvider
from events.events import SignalEvent
from ..interfaces.position_sizer_interface import IPositionSizer
from ..properties.position_sizer_properties import FixedSizingProps

class FixedSizePositionSizer(IPositionSizer):

    def __init__(self, properties: FixedSizingProps):
        """
        Initializes a FixedSizePositionSizer object.

        Args:
            properties (FixedSizingProps): The properties for the position sizer.

        Attributes:
            fixed_volume (float): The fixed volume for position sizing.
        """
        self.fixed_volume = properties.volume

    def size_signal(self, signal_event: SignalEvent, data_provider: DataProvider) -> float:
        """
        Calculate the position size based on a fixed volume.

        Parameters:
        - signal_event (SignalEvent): The signal event triggering the position sizing.
        - data_provider (DataProvider): The data provider used to retrieve market data.

        Returns:
        - float: The position size based on the fixed volume. If the fixed volume is negative, returns 0.0.
        """
        # Devolver el tamaño de posición fija
        if self.fixed_volume >= 0.0:
            return self.fixed_volume
        else:
            return 0.0