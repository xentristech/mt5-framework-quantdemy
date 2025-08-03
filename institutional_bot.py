"""Example institutional trading bot entry point."""
import os
from queue import Queue
from dotenv import load_dotenv

from platform_connector.platform_connector import PlatformConnector
from data_provider.data_provider import DataProvider
from trading_director.trading_director import TradingDirector
from signal_generator.signal_generator import SignalGenerator
from signal_generator.properties.signal_generator_properties import RSIProps
from position_sizer.position_sizer import PositionSizer
from position_sizer.properties.position_sizer_properties import FixedSizingProps
from portfolio.portfolio import Portfolio
from risk_manager.risk_manager import RiskManager
from risk_manager.properties.risk_manager_properties import MaxLeverageFactorRiskProps
from order_executor.order_executor import OrderExecutor
from notifications.notifications import NotificationService, TelegramNotificationProperties


def main() -> None:
    """Run the trading bot using configuration from environment variables."""
    # Load environment variables from a .env file, if present
    load_dotenv()

    # External service credentials
    ollama_api_url = os.getenv("OLLAMA_API_URL")
    twelvedata_api_key = os.getenv("TWELVEDATA_API_KEY")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    # Placeholder usage for unused credentials
    _ = (ollama_api_url, twelvedata_api_key)

    # Strategy configuration
    symbols = ["EURUSD", "USDJPY", "GBPUSD"]
    timeframe = "1min"
    magic_number = 12345

    events_queue = Queue()

    CONNECT = PlatformConnector(symbol_list=symbols)
    DATA_PROVIDER = DataProvider(
        events_queue=events_queue,
        symbol_list=symbols,
        timeframe=timeframe,
    )
    PORTFOLIO = Portfolio(magic_number=magic_number)
    ORDER_EXECUTOR = OrderExecutor(events_queue=events_queue, portfolio=PORTFOLIO)
    SIGNAL_GENERATOR = SignalGenerator(
        events_queue=events_queue,
        data_provider=DATA_PROVIDER,
        portfolio=PORTFOLIO,
        order_executor=ORDER_EXECUTOR,
        signal_properties=RSIProps(
            timeframe=timeframe,
            rsi_period=5,
            rsi_upper=70.0,
            rsi_lower=30.0,
            sl_points=50,
            tp_points=100,
        ),
    )
    POSITION_SIZER = PositionSizer(
        events_queue=events_queue,
        data_provider=DATA_PROVIDER,
        sizing_properties=FixedSizingProps(volume=0.05),
    )
    RISK_MANAGER = RiskManager(
        events_queue=events_queue,
        data_provider=DATA_PROVIDER,
        portfolio=PORTFOLIO,
        risk_properties=MaxLeverageFactorRiskProps(max_leverage_factor=5),
    )
    NOTIFICATIONS = NotificationService(
        properties=TelegramNotificationProperties(
            token=telegram_token,
            chat_id=telegram_chat_id,
        )
    )

    TRADING_DIRECTOR = TradingDirector(
        events_queue=events_queue,
        data_provider=DATA_PROVIDER,
        signal_generator=SIGNAL_GENERATOR,
        position_sizer=POSITION_SIZER,
        risk_manager=RISK_MANAGER,
        order_executor=ORDER_EXECUTOR,
        notification_service=NOTIFICATIONS,
    )
    TRADING_DIRECTOR.execute()


if __name__ == "__main__":
    main()
