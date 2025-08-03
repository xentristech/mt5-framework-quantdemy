# QUANTDEMY - https://quantdemy.com - Trading con Python y MetaTrader 5: Crea tu Propio Framework

from portfolio.portfolio import Portfolio
from events.events import OrderEvent, ExecutionEvent, PlacedPendingOrderEvent, SignalType
from utils.utils import Utils
import pandas as pd
from queue import Queue 
import MetaTrader5 as mt5
import time
from datetime import datetime

class OrderExecutor():

    def __init__(self, events_queue: Queue, portfolio: Portfolio) -> None:
        """
        Initialize the OrderExecutor object.

        Args:
            events_queue (Queue): The queue to receive events from.
            portfolio (Portfolio): The portfolio object to execute orders on.
        """
        self.events_queue = events_queue
        self.PORTFOLIO = portfolio

    def execute_order(self, order_event: OrderEvent) -> None:
        """
        Executes the given order event.

        Args:
            order_event (OrderEvent): The order event to be executed.

        Returns:
            None
        """

        # Evaluamos el tipo de orden que se quiere ejecutar, y llamamos al método adecuado
        if order_event.target_order == "MARKET":
            # Llamamos al método que ejecuta órdenes a mercado
            self._execute_market_order(order_event)
        else:
            # Llamamos al método que coloque órdenes pendientes
            self._send_pending_order(order_event)

    def _execute_market_order(self, order_event: OrderEvent) -> None:
        """
        Executes a market order based on the given order event.

        Args:
            order_event (OrderEvent): The order event containing the details of the market order.

        Raises:
            Exception: If the order event signal is not valid.

        Returns:
            None
        """
        # Comprobamos si la orden es de compra o de venta
        if order_event.signal == "BUY":
            # Orden de compra
            order_type = mt5.ORDER_TYPE_BUY
        elif order_event.signal == "SELL":
            # Orden de venta
            order_type = mt5.ORDER_TYPE_SELL
        else:
            raise Exception(f"ORD EXEC: La señal {order_event.signal} no es válida")

        # Creación del market order request
        market_order_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": order_event.symbol,
            "volume": order_event.volume,
            'price': mt5.symbol_info(order_event.symbol).bid,
            "sl": order_event.sl,
            "tp": order_event.tp,
            "type": order_type,
            "deviation": 0,
            "magic": order_event.magic_number,
            "comment": "FWK Market Order",
            "type_filling": mt5.ORDER_FILLING_FOK,
        }

        # Mandamos el trade request para ser ejecutado
        result = mt5.order_send(market_order_request)

        # Verificar el resultado de la ejecución de la orden
        if self._check_execution_status(result):
            print(f"{Utils.dateprint()} - Market Order {order_event.signal} para {order_event.symbol} de {order_event.volume} lotes ejecutada correctamente")
            # Generar el execution event y añadirlo a la cola
            self._create_and_put_execution_event(result)
        else:
            #Mandaremos un mensaje de error
            print(f"{Utils.dateprint()} - Ha habido un error al ejecutar la Market Order {order_event.signal} para {order_event.symbol}: {result.comment}")

    def _send_pending_order(self, order_event: OrderEvent) -> None:
        """
        Sends a pending order based on the given order event.

        Args:
            order_event (OrderEvent): The order event containing the details of the pending order.

        Raises:
            Exception: If the target order of the order event is not valid.

        Returns:
            None
        """
        # Comprobar si es de tipo STOP o de tipo LIMITE
        if order_event.target_order == "STOP":
            order_type = mt5.ORDER_TYPE_BUY_STOP if order_event.signal == "BUY" else mt5.ORDER_TYPE_SELL_STOP
        elif order_event.target_order == "LIMIT":
            order_type = mt5.ORDER_TYPE_BUY_LIMIT if order_event.signal == "BUY" else mt5.ORDER_TYPE_SELL_LIMIT
        else:
            raise Exception(f"ORD EXEC: La orden pendiente objetivo {order_event.target_order} no es válida")
        
        # Creación de la pending order request
        pending_order_request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": order_event.symbol,
            "volume": order_event.volume,
            "sl": order_event.sl,
            "tp": order_event.tp,
            "type": order_type,
            "price": order_event.target_price,
            "deviation": 0,
            "magic": order_event.magic_number,
            "comment": "FWK Pnding Order",
            "type_filling": mt5.ORDER_FILLING_FOK,
            "type_time": mt5.ORDER_TIME_GTC
        }

        # Mandamos el trade request para colocar la orden pendiente
        result = mt5.order_send(pending_order_request)

        # Verificar el resultado de la ejecución de la orden
        if self._check_execution_status(result):
            print(f"{Utils.dateprint()} - Pending Order {order_event.signal} {order_event.target_order} para {order_event.symbol} de {order_event.volume} lotes colocada en {order_event.target_price} correctamente")
            # Generamos y colocamos el evento específico de colocación de órdenes pendientes a la cola
            self._create_and_put_placed_pending_order_event(order_event)
        else:
            #Mandaremos un mensaje de error
            print(f"{Utils.dateprint()} - Ha habido un error al colocar la orden pendiente {order_event.signal} {order_event.target_order} para {order_event.symbol}: {result.comment}")
    
    def cancel_pending_order_by_ticket(self, ticket: int) -> None:
        """
        Cancels a pending order by its ticket number.

        Args:
            ticket (int): The ticket number of the pending order to be cancelled.

        Returns:
            None
        """
        # Accedemos a la orden pendiente de interés
        order = mt5.orders_get(ticket=ticket)[0]

        # Verificamos que la orden exista
        if order is None:
            print(f"{Utils.dateprint()} - ORD EXEC: No existe ninguna orden pendiente con el ticket {ticket}")
            return
        
        # Creamos el trade request para cancelar la orden pendiente
        cancel_request = {
            'action': mt5.TRADE_ACTION_REMOVE,
            'order': order.ticket,
            'symbol': order.symbol
        }

        # mandamos el cancel request
        result = mt5.order_send(cancel_request)

        # Verificar el resultado de la cancelación de la orden
        if self._check_execution_status(result):
            print(f"{Utils.dateprint()} - Orden pendiente con ticket {ticket} en {order.symbol} y volumen {order.volume_initial} se ha cancelado correctamente")
        else:
            # Mandaremos un mensaje de error
            print(f"{Utils.dateprint()} - Ha habido un error al cancelar la orden {ticket} en {order.symbol} con volumen {order.volume_initial}: {result.comment}")
    
    def close_position_by_ticket(self, ticket: int) -> None:
        """
        Closes a position by ticket number.

        Args:
            ticket (int): The ticket number of the position to be closed.

        Returns:
            None
        """
        # Accedemos a la posición de interés
        position = mt5.positions_get(ticket=ticket)[0]

        # Verificamos que la posición exista
        if position is None:
            print(f"{Utils.dateprint()} - ORD EXEC: No existe ninguna posición con el ticket {ticket}")
            return
        
        # Creamos el trade request para cerrar dicha posición
        close_request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'position': position.ticket,
            'symbol': position.symbol,
            'volume': position.volume,
            'price': mt5.symbol_info(position.symbol).bid,
            'type': mt5.ORDER_TYPE_BUY if position.type == mt5.ORDER_TYPE_SELL else mt5.ORDER_TYPE_SELL,
            'type_filling': mt5.ORDER_FILLING_FOK
        }

        # Mandamos el close_request
        result = mt5.order_send(close_request)

        # Verificar el resultado de la ejecución de la orden
        if self._check_execution_status(result):
            print(f"{Utils.dateprint()} - Posición con ticket {ticket} en {position.symbol} y volumen {position.volume} se ha cerrado correctamente")
            # Generar el execution event y añadirlo a la cola
            self._create_and_put_execution_event(result)
        else:
            # Mandaremos un mensaje de error
            print(f"{Utils.dateprint()} - Ha habido un error al cerrar la posición {ticket} en {position.symbol} con volumen {position.volume}: {result.comment}")
    
    def close_strategy_long_positions_by_symbol(self, symbol: str) -> None:
        """
        Closes all long positions for a specific symbol in the strategy's portfolio.

        Parameters:
        symbol (str): The symbol of the positions to be closed.

        Returns:
        None
        """
        # Accedemos a todas las posiciones abiertas por nuestra estrategia
        positions = self.PORTFOLIO.get_strategy_open_positions()

        # Filtrar posiciones por símbolo y por dirección
        for position in positions:
            if position.symbol == symbol and position.type == mt5.ORDER_TYPE_BUY:
                self.close_position_by_ticket(position.ticket)

    def close_strategy_short_positions_by_symbol(self, symbol: str) -> None:
        """
        Closes all short positions for a specific symbol in the strategy's portfolio.

        Parameters:
        symbol (str): The symbol of the positions to be closed.

        Returns:
        None
        """
        # Accedemos a todas las posiciones abiertas por nuestra estrategia
        positions = self.PORTFOLIO.get_strategy_open_positions()

        # Filtrar posiciones por símbolo y por dirección
        for position in positions:
            if position.symbol == symbol and position.type == mt5.ORDER_TYPE_SELL:
                self.close_position_by_ticket(position.ticket)

    def _create_and_put_placed_pending_order_event(self, order_event: OrderEvent) -> None:
        """
        Creates a PlacedPendingOrderEvent object based on the given OrderEvent and puts it in the events queue.

        Args:
            order_event (OrderEvent): The OrderEvent object containing the necessary information.

        Returns:
            None
        """
        # Creamos el placed pending order event
        placed_pending_order_event = PlacedPendingOrderEvent(
                                                        symbol=order_event.symbol,
                                                        signal=order_event.signal,
                                                        target_order=order_event.target_order,
                                                        target_price=order_event.target_price,
                                                        magic_number=order_event.magic_number,
                                                        sl=order_event.sl,
                                                        tp=order_event.tp,
                                                        volume=order_event.volume)
        
        # Lo colocamos en la events queue
        self.events_queue.put(placed_pending_order_event)
    
    def _create_and_put_execution_event(self, order_result) -> None:
        """
        Creates an execution event based on the order result and puts it into the events queue.

        Args:
            order_result (OrderResult): The result of the order execution.

        Returns:
            None
        """
        # Obtenemos la información del deal resultado de la ejecución de la orden usando la POSICIÓN a la que el deal pertenece (en lugar del ticket del propio deal),
        # ya que en LIVE el resultado del deal suele ser 0 si lo consultamos inmediatamente.
        #deal = mt5.history_deals_get(ticket=order_result.deal)[0]
        deal = None

        # Simulamos un fill_time usando el momento actual
        fill_time = datetime.now()
        
        # Creamos un pequeño bucle para dar tiempo al servidor a que genere el deal, y definimos un máximo de 5 intentos
        for _ in range(5):
            # Esperamos 0.5 segundos
            time.sleep(0.5)
            try:
                deal = mt5.history_deals_get(position=order_result.order)[0]  # Usamos position en lugar de ticket
            except IndexError:
                deal = None
                
            if not deal:
                # Si no obtenemos el deal, vamos a guardar el fill time como "ahora" para tener una aproximación -> puedes modificarlo si lo consideras necesario
                fill_time = datetime.now()
                continue
            else:
                break
        
        # Si pasado el bucle no hemos obtenido el deal, mostramos un mensaje de error
        if not deal:
            print(f"{Utils.dateprint()} - ORD EXEC: No se ha podido obtener el deal de la ejecución de la orden {order_result.order}, aunque probablemente haya sido ejecutada.")

        # Creamos el execution event
        execution_event = ExecutionEvent(symbol=order_result.request.symbol,
                                        signal=SignalType.BUY if order_result.request.type == mt5.DEAL_TYPE_BUY else SignalType.SELL,
                                        fill_price=order_result.price,
                                        fill_time=fill_time if not deal else pd.to_datetime(deal.time_msc, unit='ms'),
                                        volume=order_result.request.volume)
        
        # Colocar el execution event a la cola de eventos
        self.events_queue.put(execution_event)

    def _check_execution_status(self, order_result) -> bool:
        """
        Checks the execution status of an order.

        Args:
            order_result (mt5.TradeResult): The result of the order execution.

        Returns:
            bool: True if the execution status is successful, False otherwise.
        """
        if order_result.retcode == mt5.TRADE_RETCODE_DONE:
            # todo ha ido bien
            return True
        elif order_result.retcode == mt5.TRADE_RETCODE_DONE_PARTIAL:
            return True
        else:
            return False

