import configparser
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict

from binance import Client

from binance_trade_bot.config import Config
from binance_trade_bot.database import Pair, Database, Coin, Trade
from binance_trade_bot.logger import Logger


# def get_remote_pair_information_from_nexus(database: str, table: str) -> List: 
#     conn = sqlite3.connect(database)
#     # Use the connection to execute SQL queries
#     cursor = conn.cursor()
#     cursor.execute(f'SELECT * FROM {table}')
#     results = cursor.fetchall()
#     
#     # Close the connection and the SSH tunnel
#     conn.close()
#     return results

def delete_and_reinsert_into_pairs_table(database: str, coin_pairs: List[Pair]) -> List:
    """
    Delete all records from the 'pairs' table in the specified database and reinsert the given coin pairs.

    Args:
        database (str): The path to the SQLite database file.
        coin_pairs (List[Pair]): A list of Pair objects representing the coin pairs to be inserted.

    Returns:
        List: An empty list.

    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM pairs')
    insert_list = [(idx + 1, coin.from_coin.symbol, coin.to_coin.symbol, coin.ratio) for idx, coin in
                   enumerate(coin_pairs)]
    insert_command = "INSERT INTO %s VALUES (?,?,?,?)" % 'pairs'
    cursor.executemany(insert_command, insert_list)
    conn.commit()
    conn.close()



def insert_into_trade_history_table(database: str, coin_pairs: List[Trade]) -> List:
    conn = sqlite3.connect(database)
    # Use the connection to execute SQL queries
    cursor = conn.cursor()
    cursor.execute('DELETE FROM trade_history')
    insert_list = [(idx + 1, coin.alt_coin_id, coin.crypto_coin_id, coin.selling, coin.state.value,
                    coin.alt_starting_balance, coin.alt_trade_amount, coin.crypto_starting_balance,
                    coin.crypto_trade_amount, coin.datetime) for idx, coin in enumerate(coin_pairs)]
    insert_command = "INSERT INTO %s VALUES (?,?,?,?,?,?,?,?,?,?)" % 'trade_history'

    cursor.executemany(insert_command, insert_list)
    conn.commit()
    conn.close()


def update_last_row_in_trade_history_table(database: str,
                                           alt_trade_amount: float,
                                           crypto_starting_balance: float,
                                           crypto_trade_amount: float,
                                           datetime: str):
    '''def delete_and_reinsert_into_pairs_table(database: str, coin_pairs: List[Pair]) -> List:
    """
    Delete all records from the 'pairs' table in the specified database and reinsert the given coin pairs.

    Args:
        database (str): The path to the SQLite database file.
        coin_pairs (List[Pair]): A list of Pair objects representing the coin pairs to be inserted.

    Returns:
        List: An empty list.

    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM pairs')
    insert_list = [(idx + 1, coin.from_coin.symbol, coin.to_coin.symbol, coin.ratio) for idx, coin in
                   enumerate(coin_pairs)]
    insert_command = "INSERT INTO %s VALUES (?,?,?,?)" % 'pairs'
    cursor.executemany(insert_command, insert_list)
    conn.commit()
    conn.close()

    1. Select last row from table trade_history
    2. Update the row with new values
    '''
    conn = sqlite3.connect(database)
    # Use the connection to execute SQL queries
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM trade_history ORDER BY datetime DESC LIMIT 1')
    last_row = cursor.fetchone()
    print(f'Last row in trade_history table: {last_row}')
    cursor.execute(
        'UPDATE trade_history SET alt_trade_amount=?, crypto_starting_balance=?, crypto_trade_amount=?, datetime=? WHERE id=?',
        (alt_trade_amount, crypto_starting_balance, crypto_trade_amount, datetime, last_row[0]))
    conn.commit()
    conn.close()


def create_coin_pairs(coin_list: List[Coin], coin_price: Dict[str, float]) -> List[Pair]:
    pairs = []
    for from_coin in coin_list:
        for to_coin in coin_list:
            if from_coin.symbol != to_coin.symbol:
                ratio = coin_price[from_coin.symbol + 'USDT'] / coin_price[to_coin.symbol + 'USDT']
                pairs.append(Pair(from_coin, to_coin, ratio))
    return pairs


def find_ticker_price_at_specific_date_time_at_binance(pairs: List[str], date_time: str, client: Client):
    end_time = (datetime.fromisoformat(date_time) + timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
    result = {}
    for pair in pairs:
        print(f'Downloading {pair} price at {date_time}')
        klines = client.get_historical_klines(symbol=pair,
                                              interval=Client.KLINE_INTERVAL_1MINUTE,
                                              start_str=date_time,
                                              end_str=end_time,
                                              limit=1)
        kline = klines[0]
        price = max([
            float(kline[1]),
            float(kline[2]),
            float(kline[3]),
            float(kline[4]),
        ])  ## assume the worst, get the max of open, high, low and close
        '''
            [
                1615388800000,   # 0 Timestamp 
                0.00007456,      # 1 Open price
                0.00007456,      # 2 High price
                0.00007456,      # 3 Low price
                0.00007456,      # 4 Close price
                50.00000000,     # 5 Volume
                1615389199999,   # 6 Close time
                0.36000000,      # 7 Quote asset volume
                2,               # 8 Number of trades
                50.00000000,     # 9 Taker buy base asset volume
                0.36000000,      # 10 Taker buy quote asset volume
                None             # 11 Ignore
              ],
        '''
        result[pair] = price
    return result


database_file = 'C:\\AgodaGit\\binance-trade-bot\\data\\crypto_trading.db'
purchase_time = '2022-11-09 22:57:00'
alt_trade_amount = 63.73831045406546
crypto_starting_balance = 754.1866
crypto_trade_amount = 754.1866

config_file_name = "../user.cfg"
user_config_section = "binance_user_config"
config = configparser.ConfigParser()
config.read(config_file_name)

api_key = config.get(user_config_section, "api_key")
api_secret = config.get(user_config_section, "api_secret_key")
client = Client(api_key, api_secret)
binance_client = Client(api_key=api_key, api_secret=api_secret)
'''
Steps :
1. Get the list of pairs from the database
2. Download the historical data from binance for all pairs
3. Calculate ratio of each pair
'''
logger = Logger()
config = Config(config_file_path=config_file_name)
database = Database(logger, config, uri=f'sqlite:///{database_file}')

# result = get_remote_pair_information_from_nexus('C:\\AgodaGit\\binance-trade-bot\\data\\crypto_trading.db', 'pairs')
# print(result)
coin_list: List[Coin] = database.get_coins()  # get_all_enabled_pairs_from_sqlite(database_file)

coin_price = find_ticker_price_at_specific_date_time_at_binance([s.symbol + 'USDT' for s in coin_list],
                                                                purchase_time,
                                                                binance_client)
coin_pairs = create_coin_pairs(coin_list, coin_price)
print(coin_pairs)
delete_and_reinsert_into_pairs_table(database_file, coin_pairs)
update_last_row_in_trade_history_table(database_file, alt_trade_amount, crypto_starting_balance, crypto_trade_amount,
                                       purchase_time)
