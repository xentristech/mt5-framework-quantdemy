# QUANTDEMY - https://quantdemy.com - Trading con Python y MetaTrader 5: Crea tu Propio Framework

from data_provider.data_provider import DataProvider
from events.events import SignalEvent
from ..interfaces.position_sizer_interface import IPositionSizer
from ..properties.position_sizer_properties import RiskPctSizingProps
from utils.utils import Utils
import MetaTrader5 as mt5

class RiskPctPositionSizer(IPositionSizer):

    def __init__(self, properties: RiskPctSizingProps):
        """
        Initializes a RiskPctPositionSizer object.

        Args:
            properties (RiskPctSizingProps): An object containing the properties for risk percentage position sizing.
        """
        self.risk_pct = properties.risk_pct

    def size_signal(self, signal_event: SignalEvent, data_provider: DataProvider) -> float:
        """
        Calculates the size of the position based on the risk percentage and signal event data.

        Args:
            signal_event (SignalEvent): The signal event containing information about the trade.
            data_provider (DataProvider): The data provider used to retrieve market data.

        Returns:
            float: The size of the position.

        Raises:
            None.
        """
        # Revisar que el riesgo sea positivo
        if self.risk_pct <= 0.0:
            print(f"{Utils.dateprint()} - ERROR (RiskPctPositionSizer): El porcentaje de riesgo introducido: {self.risk_pct} no es válido.")
            return 0.0

        # Revisar que el sl != 0
        if signal_event.sl <= 0.0:
            print(f"{Utils.dateprint()} - ERROR (RiskPctPositionSizer): El valor del SL: {signal_event.sl} no es válido.")
            return 0.0
        
        # Acceder a la información de la cuenta (para obtener divisa de la cuenta)
        account_info = mt5.account_info()
        
        # Acceder a la información del símbolo (para poder calcular el riesgo)
        symbol_info = mt5.symbol_info(signal_event.symbol)

        
        # Recuperamos el precio de entrada estimado:
        # Si es una orden a mercado
        if signal_event.target_order == "MARKET":
            # Obtener el último precio disponible en el mercado (ask o bid)
            last_tick = data_provider.get_latest_tick(signal_event.symbol)
            entry_price = last_tick['ask'] if signal_event.signal == "BUY" else last_tick['bid']
        
        # Si es una orden pendiente (limit o stop)
        else:
            # Cogemos el precio del propio signal event
            entry_price = signal_event.target_price

        # Conseguimos los valores que nos faltan para los cálculos
        equity = account_info.equity
        volume_step = symbol_info.volume_step               # Cambio mínimo de volumen
        tick_size = symbol_info.trade_tick_size             # Cambio mínimo de precio
        account_ccy = account_info.currency                 # divisa de la cuenta
        symbol_profit_ccy = symbol_info.currency_profit     # divisa del profit del símbolo
        contract_size = symbol_info.trade_contract_size     # tamaño del contrato (ej 1 lote estándar)

        # Cálculos auxiliares
        tick_value_profit_ccy = contract_size * tick_size              # Cantidad ganada o perdida por cada lote y por cada tick

        # Convertick el tick value en profit ccy del symbol a la divisa de nuestra cuenta
        tick_value_account_ccy = Utils.convert_currency_amount_to_another_currency(tick_value_profit_ccy, symbol_profit_ccy, account_ccy)
        
        # Cálculo del tamaño de la posición
        try:
            price_distance_in_integer_ticksizes = int(abs(entry_price - signal_event.sl) / tick_size)
            monetary_risk = equity * self.risk_pct
            volume = monetary_risk / (price_distance_in_integer_ticksizes * tick_value_account_ccy)
            volume = round(volume / volume_step) * volume_step
        
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Problema al calcular el tamaño de la posición en función del riesgo. Excepción: {e}")
            return 0.0

        else:
            return volume