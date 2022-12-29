# IMPORTS
import math
import os.path
import sqlite3
from datetime import datetime

import pandas as pd
from binance.client import Client
from dateutil import parser

binance_api_key = '[REDACTED]'  # Enter your own API-key here
binance_api_secret = '[REDACTED]'  # Enter your own API-secret here

### CONSTANTS
binsizes = {"1m": 1}
batch_size = 800
binance_client = Client(api_key=binance_api_key, api_secret=binance_api_secret)


### FUNCTIONS
def minutes_of_new_data(symbol, kline_size, data, source):
    if len(data) > 0:
        old = parser.parse(data["timestamp"].iloc[-1])
    elif source == "binance":
        old = datetime.strptime('1 Jan 2017', '%d %b %Y')
    if source == "binance": new = pd.to_datetime(binance_client.get_klines(symbol=symbol, interval=kline_size)[-1][0],
                                                 unit='ms')
    return old, new


def get_all_binance(symbol, kline_size, save=False):
    filename = '%s-%s-data.csv' % (symbol, kline_size)
    if os.path.isfile(filename):
        data_df = pd.read_csv(filename)
    else:
        data_df = pd.DataFrame()
    oldest_point, newest_point = minutes_of_new_data(symbol, kline_size, data_df, source="binance")
    delta_min = (newest_point - oldest_point).total_seconds() / 60
    available_data = math.ceil(delta_min / binsizes[kline_size])
    if oldest_point == datetime.strptime('1 Jan 2017', '%d %b %Y'):
        print('Downloading all available %s data for %s. Be patient..!' % (kline_size, symbol))
    else:
        print('Downloading %d minutes of new data available for %s, i.e. %d instances of %s data.' % (
            delta_min, symbol, available_data, kline_size))
    klines = binance_client.get_historical_klines(symbol, kline_size, oldest_point.strftime("%d %b %Y %H:%M:%S"),
                                                  newest_point.strftime("%d %b %Y %H:%M:%S"))
    data = pd.DataFrame(klines,
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av',
                                 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
    if len(data_df) > 0:
        temp_df = pd.DataFrame(data)
        data_df = data_df.append(temp_df)
    else:
        data_df = data
    data_df.set_index('timestamp', inplace=True)
    if save: data_df.to_csv(filename)
    print('All caught up..!')
    return data_df


def download_spot_trading_history_for_pair(pair: str, api_key: str, api_secret: str, frm: str, to: str):
    '''
    Download spot trading history for a given pair
    '''
    client = Client(api_key, api_secret)
    trades = client.get_my_trades(symbol=pair, startTime=frm, endTime=to)


def get_current_exchange_rate_from_binance(pair: str):
    '''
    Get current exchange rate from binance
    '''
    client = Client(binance_api_key, binance_api_secret)
    # return client.get_symbol_ticker(symbol=pair)


def copy_sqlite_table_rows_between_two_database(from_db: str, to_db: str, table_name: str):
    '''
    Copy sqlite table rows between two database
    '''
    from_conn = sqlite3.connect(from_db)
    to_conn = sqlite3.connect(to_db)

    '''
    Get table names from from_db
    '''
    from_cursor = from_conn.cursor()
    from_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    from_tables = from_cursor.fetchall()

    for i in from_tables:
        if i[0] == table_name:
            from_cursor.execute("SELECT * FROM " + table_name)
            rows = from_cursor.fetchall()
            to_cursor = to_conn.cursor()
            to_cursor.execute("DELETE FROM " + table_name)
            to_conn.commit()
            to_cursor.executemany("INSERT INTO " + table_name + " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
            to_conn.commit()
            to_cursor.close()
            break

    from_conn.row_factory = sqlite3.Row
    cur = from_conn.cursor()
    cur.execute("SELECT * FROM %s" % table_name)
    rows = cur.fetchall()
    '''
    First truncate table before executing insert
    '''
    to_cursor = to_conn.cursor()
    to_cursor.execute("DELETE FROM " + table_name)
    to_conn.commit()
    to_conn.executemany("INSERT INTO %s VALUES (?,?,?,?,?,?,?,?,?)" % table_name, rows)
    to_conn.commit()
    from_conn.close()
    to_conn.close()
