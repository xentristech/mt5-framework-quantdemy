# QUANTDEMY - https://quantdemy.com - Trading con Python y MetaTrader 5: Crea tu Propio Framework

from utils.utils import Utils
import MetaTrader5 as mt5
import pandas as pd
from typing import Dict
from datetime import datetime
from events.events import DataEvent
from queue import Queue


class DataProvider():

    def __init__(self, events_queue: Queue, symbol_list: list, timeframe: str):
        """
        Initialize the DataProvider object.

        Args:
            events_queue (Queue): The queue to store the events.
            symbol_list (list): The list of symbols to fetch data for.
            timeframe (str): The timeframe for the data.

        Attributes:
            events_queue (Queue): The queue to store the events.
            symbols (list): The list of symbols to fetch data for.
            timeframe (str): The timeframe for the data.
            last_bar_datetime (Dict[str, datetime]): A dictionary to store the last seen datetime for each symbol.
        """
        self.events_queue = events_queue
        self.symbols: list = symbol_list
        self.timeframe: str = timeframe

        # Creamos un diccionario para guardar el datetime de la última vela que habíamos visto para cada símbolo
        self.last_bar_datetime: Dict[str, datetime] = {symbol: datetime.min for symbol in self.symbols}

    def _map_timeframes(self, timeframe: str) -> int:
        """
        Maps a string timeframe to its corresponding integer value.

        Args:
            timeframe (str): The string representation of the timeframe.

        Returns:
            int: The integer value of the mapped timeframe.

        Raises:
            None

        """
        timeframe_mapping = {
            '1min': mt5.TIMEFRAME_M1,
            '2min': mt5.TIMEFRAME_M2,                        
            '3min': mt5.TIMEFRAME_M3,                        
            '4min': mt5.TIMEFRAME_M4,                        
            '5min': mt5.TIMEFRAME_M5,                        
            '6min': mt5.TIMEFRAME_M6,                        
            '10min': mt5.TIMEFRAME_M10,                       
            '12min': mt5.TIMEFRAME_M12,
            '15min': mt5.TIMEFRAME_M15,
            '20min': mt5.TIMEFRAME_M20,                       
            '30min': mt5.TIMEFRAME_M30,                       
            '1h': mt5.TIMEFRAME_H1,                          
            '2h': mt5.TIMEFRAME_H2,                          
            '3h': mt5.TIMEFRAME_H3,                          
            '4h': mt5.TIMEFRAME_H4,                          
            '6h': mt5.TIMEFRAME_H6,                          
            '8h': mt5.TIMEFRAME_H8,                          
            '12h': mt5.TIMEFRAME_H12,
            '1d': mt5.TIMEFRAME_D1,                       
            '1w': mt5.TIMEFRAME_W1,                       
            '1M': mt5.TIMEFRAME_MN1,                       
        }

        try:
            return timeframe_mapping[timeframe]
        except:
            print(f"{Utils.dateprint()} - Timeframe {timeframe} no es válido.")
    
    def get_latest_closed_bar(self, symbol: str, timeframe: str) -> pd.Series:
        """
        Retrieves the latest closed bar for a given symbol and timeframe.

        Args:
            symbol (str): The symbol to retrieve the bar data for.
            timeframe (str): The timeframe of the bars.

        Returns:
            pd.Series: The latest closed bar data as a pandas Series object.
        """
        
        # Definir los parámetros adecuados
        tf = self._map_timeframes(timeframe)
        from_position = 1
        num_bars = 1
        
        # Recuperamos los datos de la última vela
        try:
            bars_np_array = mt5.copy_rates_from_pos(symbol, tf, from_position, num_bars)
            if bars_np_array is None:
                print(f"{Utils.dateprint()} - El símbolo {symbol} no existe o no se han podido recuperar su datos")

                # Vamos a devolver una Series empty
                return pd.Series()

            bars = pd.DataFrame(bars_np_array)

            # Convertimos la columna time a datetime y la hacemos el índice
            bars['time'] = pd.to_datetime(bars['time'], unit='s')
            bars.set_index('time', inplace=True)

            # Cambiamos nombres de columnas y las reorganizamos
            bars.rename(columns={'tick_volume': 'tickvol', 'real_volume': 'vol'}, inplace=True)
            bars = bars[['open', 'high', 'low', 'close', 'tickvol', 'vol', 'spread']]
        
        except Exception as e:
            print(f"{Utils.dateprint()} - No se han podido recuperar los datos de la última vela de {symbol} {timeframe} - MT5 Error: {mt5.last_error()}, exception: {e}")
        
        else:
            # Si el DF está vacío, devolvemos una serie vacía
            if bars.empty:
                return pd.Series()
            else:
                return bars.iloc[-1]

    def get_latest_closed_bars(self, symbol: str, timeframe: str, num_bars: int = 1) -> pd.DataFrame:
        """
        Retrieves the latest closed bars for a given symbol and timeframe.

        Args:
            symbol (str): The symbol to retrieve bars for.
            timeframe (str): The timeframe of the bars (e.g., 'M1', 'H1', 'D1').
            num_bars (int, optional): The number of bars to retrieve. Defaults to 1.

        Returns:
            pd.DataFrame: A DataFrame containing the latest closed bars data.

        Raises:
            Exception: If the data retrieval fails.

        """

        # Definir los parámetros adecuados
        tf = self._map_timeframes(timeframe)
        from_position = 1
        bars_count = num_bars if num_bars > 0 else 1

        # Recuperamos los datos de la última vela
        try:
            bars_np_array = mt5.copy_rates_from_pos(symbol, tf, from_position, bars_count)
            if bars_np_array is None:
                print(f"{Utils.dateprint()} - El símbolo {symbol} no existe o no se han podido recuperar su datos")

                # Vamos a devolver un DataFrame empty
                return pd.DataFrame()

            bars = pd.DataFrame(bars_np_array)

            # Convertimos la columna time a datetime y la hacemos el índice
            bars['time'] = pd.to_datetime(bars['time'], unit='s')
            bars.set_index('time', inplace=True)

            # Cambiamos nombres de columnas y las reorganizamos
            bars.rename(columns={'tick_volume': 'tickvol', 'real_volume': 'vol'}, inplace=True)
            bars = bars[['open', 'high', 'low', 'close', 'tickvol', 'vol', 'spread']]
        
        except Exception as e:
            print(f"{Utils.dateprint()} - No se han podido recuperar los datos de la última vela de {symbol} {timeframe} - MT5 Error: {mt5.last_error()}, exception: {e}")
        
        else:
            # Si todo OK, devolvemos el dataframe con las num_bars
            return bars
        
    def get_latest_tick(self, symbol: str) -> dict:
        """
        Retrieves the latest tick for the given symbol.

        Parameters:
        symbol (str): The symbol for which to retrieve the latest tick.

        Returns:
        dict: A dictionary containing the latest tick information.
        """
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                print(f"{Utils.dateprint()} - {Utils.dateprint()} - No se ha podido recuperar el último tick de {symbol} - MT5 error: {mt5.last_error()}")
                return {}
        
        except Exception as e:
            print(f"{Utils.dateprint()} - Algo no ha ido bien a la hora de recuperar el último tick de {symbol}. MT5 error: {mt5.last_error()}, exception: {e}")
        
        else:
            return tick._asdict()
    
    def check_for_new_data(self) -> None:
        """
        Checks for new data for each symbol and adds it to the events queue if available.

        This method iterates over the symbols and checks if there is new data available for each symbol.
        If new data is found, it updates the last retrieved bar for the symbol and adds a DataEvent to the events queue.

        Returns:
            None
        """
        for symbol in self.symbols:
            latest_bar = self.get_latest_closed_bar(symbol, self.timeframe)

            if latest_bar is None:
                continue

            if not latest_bar.empty and latest_bar.name > self.last_bar_datetime[symbol]:
                self.last_bar_datetime[symbol] = latest_bar.name
                data_event = DataEvent(symbol=symbol, data=latest_bar)
                self.events_queue.put(data_event)
