'''

Steps:
1. Delete C:\AgodaGit\binance-trade-bot\data\crypto_trading.db and run binante_trade_bot to generate a fresh database
2. Copy all data from C:\AgodaGit\binance-trade-bot\data2\crypto_trading.db to C:\AgodaGit\binance-trade-bot\data\crypto_trading.db
4. Fill in trade history
3. Fill in pairs
'''

import configparser
import sqlite3
from datetime import datetime

import pandas as pd
from binance import Client
from pandas import json_normalize

CFG_FL_NAME = "../user.cfg"
USER_CFG_SECTION = "binance_user_config"
config = configparser.ConfigParser()
config.read(CFG_FL_NAME)

api_key = config.get(USER_CFG_SECTION, "api_key")
api_secret = config.get(USER_CFG_SECTION, "api_secret_key")
client = Client(api_key, api_secret)


class Trade:
    def __init__(self, alt_coin_id, crypto_coin_id, selling, state, alt_starting_balance, alt_trade_amount,
                 crypto_starting_balance, crypto_trade_amount, datetime):
        self.alt_coin_id = alt_coin_id
        self.crypto_coin_id = crypto_coin_id
        self.selling = selling
        self.state = state
        self.alt_starting_balance = alt_starting_balance
        self.alt_trade_amount = alt_trade_amount
        self.crypto_starting_balance = crypto_starting_balance
        self.crypto_trade_amount = crypto_trade_amount
        self.datetime = datetime

    def to_tuple(self):
        return (self.alt_coin_id, self.crypto_coin_id, self.selling, self.state, self.alt_starting_balance,
                self.alt_trade_amount, self.crypto_starting_balance, self.crypto_trade_amount, self.datetime)


# download ohlc candle at specific timestamp from binance
def download_ohlc_1_min_candle_from_binance_for_pair_at_timestamp(pair: str, timestamp: int):
    # download the klines (OHLC candles) for the given symbol and timestamp
    klines = client.get_historical_klines(
        symbol=pair,
        interval=Client.KLINE_INTERVAL_1MINUTE,
        start_str=timestamp,
        end_str=timestamp + 1 * 60 * 1000  # 1 minute, 1 candle
    )
    # extract the closing price from the klines
    closing_price = float(klines[0][4])

    return closing_price


def download_spot_trading_history_for_pair(pair: str, frm: int):
    trades = client.get_my_trades(symbol=pair, startTime=frm)
    trades_df = json_normalize(trades)
    df = trades_df  # .query(f'isBuyer == {is_buyer}')
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df[['price', 'qty', 'quoteQty']] = df[['price', 'qty', 'quoteQty']].apply(
        lambda x: pd.to_numeric(x, errors='coerce'))
    df.sort_values(by='time', ascending=False, inplace=True)
    df['buy_sell'] = df['isBuyer'].apply(lambda x: 'BUY' if x else 'SELL')
    return df


def convert_to_unix_timestamp(date_time_str):
    date_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f')
    timestamp = int(date_obj.timestamp()) * 1000
    return timestamp


def copy_data():
    # Connect to source database and retrieve cursor
    src_conn = sqlite3.connect(r"C:\AgodaGit\binance-trade-bot\data2\crypto_trading.db")
    src_cursor = src_conn.cursor()

    # Connect to target database and retrieve cursor
    tgt_conn = sqlite3.connect(r"C:\AgodaGit\binance-trade-bot\data\crypto_trading.db")
    tgt_cursor = tgt_conn.cursor()

    # Define table names to copy
    table_names = ["coins", "current_coin_history", "trade_history"]

    # Loop through each table and copy data
    for table_name in table_names:
        # Delete existing data in target table
        tgt_cursor.execute(f"DELETE FROM {table_name}")

        # Copy data from source table to target table
        print(f'Copying from {table_name}')
        src_cursor.execute(f"SELECT * FROM {table_name}")
        rows = src_cursor.fetchall()
        tgt_cursor.executemany(f"INSERT INTO {table_name} VALUES ({','.join('?' * len(rows[0]))})", rows)

    # Commit changes and close connections
    tgt_conn.commit()
    tgt_conn.close()
    src_conn.close()


def fill_trade_history():
    plan = ['SOL', 'MANA', 'SAND']
    start_from_timestamp = convert_to_unix_timestamp('2022-11-11 15:57:51.295')  # '2022-11-09 15:57:51.295'
    result = download_spot_trading_history_for_pair(f'{plan[0]}USDT', start_from_timestamp)

    for p in plan[1:]:
        result = result.append(download_spot_trading_history_for_pair(f'{p}USDT', start_from_timestamp))

    result.sort_values(by='time', ascending=True, inplace=True)

    rows = []
    previous_symbol = ''
    previous_side = ''
    for index, row in result.iterrows():
        current_symbol = row['symbol'].replace('USDT', '')
        current_side = 'BUY' if row['isBuyer'] else 'SELL'

        # print bought or sold coin based on symbol and side value
        # print('current_symbol: {}, current_side: {} , previous_coin: {}, previous_side: {}'
        #       .format(current_symbol, current_side, previous_symbol, previous_side))

        same_symbol = previous_symbol == current_symbol
        same_side = previous_side == current_side

        if same_symbol and same_side:
            # print('Same')
            current_trade_history: Trade = rows[-1]
            current_trade_history.alt_starting_balance += row['qty']
            current_trade_history.alt_trade_amount += row['qty']

            current_trade_history.crypto_starting_balance += row['quoteQty']
            current_trade_history.crypto_trade_amount += row['quoteQty']
        else:
            # print('Different')
            current_trade_history = Trade(
                alt_coin_id=current_symbol,
                crypto_coin_id='USDT',
                selling=not row['isBuyer'],
                state='COMPLETE',
                alt_starting_balance=row['qty'],
                alt_trade_amount=row['qty'],
                crypto_starting_balance=row['quoteQty'],
                crypto_trade_amount=row['quoteQty'],
                datetime=row['timestamp']
            )
            rows.append(current_trade_history)

        previous_symbol = current_symbol
        previous_side = current_side

    for r in rows:
        print(r.to_tuple())

    db_file_path = r'C:\AgodaGit\binance-trade-bot\data\crypto_trading.db'
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM trade_history ORDER BY datetime DESC LIMIT 1')
    last_row = cursor.fetchone()
    last_index = last_row[0]

    insert_list = [(last_index + idx + 1,
                    coin.alt_coin_id,
                    coin.crypto_coin_id,
                    coin.selling,
                    coin.state,
                    coin.alt_starting_balance,
                    coin.alt_trade_amount,
                    coin.crypto_starting_balance,
                    coin.crypto_trade_amount,
                    coin.datetime.strftime('%Y-%m-%d %H:%M:%S')
                    ) for idx, coin in enumerate(rows)]

    insert_command = "INSERT INTO trade_history VALUES (?,?,?,?,?,?,?,?,?,?)"
    for i in insert_list:
        # print(insert_command)
        cursor.execute(insert_command, i)

    conn.commit()
    conn.close()


def fill_pair():
    db_file_path = r'C:\AgodaGit\binance-trade-bot\data\crypto_trading.db'
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()
    cursor.execute('SELECT datetime FROM trade_history ORDER BY datetime DESC LIMIT 1')
    last_row = cursor.fetchone()
    last_purchase = last_row[0]

    enabled_coins = cursor.execute('SELECT symbol from coins where enabled = 1').fetchall()
    enabled_coins = [item for tpl in enabled_coins for item in tpl]

    coin_price = {}
    timestamp = int(datetime.strptime(last_purchase, "%Y-%m-%d %H:%M:%S").timestamp()) * 1000
    for coin in enabled_coins:
        coin_price[coin] = download_ohlc_1_min_candle_from_binance_for_pair_at_timestamp(f'{coin}USDT', timestamp)

    # calculate all ratios
    pairs = {}
    for from_coin in enabled_coins:
        for to_coin in enabled_coins:
            if from_coin != to_coin:
                pair = (from_coin, to_coin)
                ratio = coin_price[from_coin] / coin_price[to_coin]
                pairs[pair] = ratio

    cursor.execute('DELETE FROM pairs')
    insert_list = [(index + 1, pair[0], pair[1], ratio,) for index, (pair, ratio) in
                   enumerate(pairs.items())]

    insert_command = "INSERT INTO pairs VALUES (?,?,?,?)"
    for i in insert_list:
        # print(insert_command)
        cursor.execute(insert_command, i)

    conn.commit()
    conn.close()
    # pairs
    #
    # db_file_path = r'C:\AgodaGit\binance-trade-bot\data\crypto_trading.db'
    # conn = sqlite3.connect(db_file_path)
    # cursor = conn.cursor()
    # cursor.execute('DELETE FROM pairs')


# 2 copy data
copy_data()
# 3 fill trade history
fill_trade_history()
# 4 fill pair
fill_pair()
