# QUANTDEMY - https://quantdemy.com - Trading con Python y MetaTrader 5: Crea tu Propio Framework

from pydantic import BaseModel

class BaseRiskProps(BaseModel):
    pass

class MaxLeverageFactorRiskProps(BaseRiskProps):
    """
    Risk properties for managing maximum leverage factor.
    """

    max_leverage_factor: float