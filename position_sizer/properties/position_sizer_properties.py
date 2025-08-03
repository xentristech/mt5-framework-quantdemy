# QUANTDEMY - https://quantdemy.com - Trading con Python y MetaTrader 5: Crea tu Propio Framework

from pydantic import BaseModel

class BaseSizerProps(BaseModel):
    pass

class MinSizingProps(BaseSizerProps):
    pass

class FixedSizingProps(BaseSizerProps):
    """
    Represents the properties for fixed sizing of positions.

    Attributes:
        volume (float): The fixed volume for each position.
    """
    volume: float

class RiskPctSizingProps(BaseSizerProps):
    """
    Properties for risk percentage position sizing.

    Attributes:
        risk_pct (float): The risk percentage for position sizing.
    """
    risk_pct: float