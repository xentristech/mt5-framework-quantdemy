# QUANTDEMY - https://quantdemy.com - Trading con Python y MetaTrader 5: Crea tu Propio Framework

from utils.utils import Utils
from events.events import SizingEvent
from ..interfaces.risk_manager_interface import IRiskManager
from ..properties.risk_manager_properties import MaxLeverageFactorRiskProps
import MetaTrader5 as mt5
import sys

class MaxLeverageFactorRiskManager(IRiskManager):

    def __init__(self, properties: MaxLeverageFactorRiskProps):
        """
        Initializes a MaxLeverageFactorRiskManager object.

        Args:
            properties (MaxLeverageFactorRiskProps): The properties object containing the maximum leverage factor.
        """
        self.max_leverage_factor = properties.max_leverage_factor

    def _compute_leverage_factor(self, account_value_acc_ccy: float) -> float:
        """
        Computes the leverage factor based on the account value and equity.

        Args:
            account_value_acc_ccy (float): The account value in the account currency.

        Returns:
            float: The computed leverage factor.
        """

        account_equity = mt5.account_info().equity

        if account_equity <= 0:
            return sys.float_info.max
        else:
            return account_value_acc_ccy / account_equity

    def _check_expected_new_position_is_compliant_with_max_leverage_factor(self, sizing_event: SizingEvent, 
                                                                            current_positions_value_acc_ccy: float,
                                                                            new_position_value_acc_ccy: float) -> bool:
        """
        Checks if the expected new position is compliant with the maximum leverage factor.

        Args:
            sizing_event (SizingEvent): The sizing event for the new position.
            current_positions_value_acc_ccy (float): The current value of all positions in the account currency.
            new_position_value_acc_ccy (float): The value of the new position in the account currency.

        Returns:
            bool: True if the new position is compliant with the maximum leverage factor, False otherwise.
        """
        # Calculamos el nuevo expected account value que tendría la cuenta si ejecutáramos la nueva posición
        new_account_value = current_positions_value_acc_ccy + new_position_value_acc_ccy

        # Calculamos el nuevo factor de apalancamiento que tendríamos SI EJECUTÁRAMOS esa posición
        new_leverage_factor = self._compute_leverage_factor(new_account_value)

        # Comprobamos si el nuevo leverage factor sería mayor a nuestro máximo leverage factor
        if abs(new_leverage_factor) <= self.max_leverage_factor:
            return True
        else:
            print(f"{Utils.dateprint()} - RISK MGMT: La posición objetivo {sizing_event.signal} {sizing_event.volume} implica un Leverage Factor de {abs(new_leverage_factor):.2f}, que supera el máx. de {self.max_leverage_factor}")
            return False

    def assess_order(self, sizing_event: SizingEvent, current_positions_value_acc_ccy: float, new_position_value_acc_ccy: float) -> float:
        """
        Assess the order and determine whether it should be allowed or not based on the maximum leverage factor.

        Args:
            sizing_event (SizingEvent): The sizing event for the order.
            current_positions_value_acc_ccy (float): The current value of all positions in the account currency.
            new_position_value_acc_ccy (float): The value of the new position in the account currency.

        Returns:
            float: The volume of the order if it is compliant with the maximum leverage factor, otherwise 0.0.
        """
        if self._check_expected_new_position_is_compliant_with_max_leverage_factor(sizing_event, current_positions_value_acc_ccy, new_position_value_acc_ccy):
            return sizing_event.volume
        else:
            return 0.0