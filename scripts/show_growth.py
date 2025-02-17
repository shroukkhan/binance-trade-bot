import configparser
import sqlite3
import time
from datetime import datetime
from datetime import timedelta

import pytz
import requests
from binance.client import Client
from dateutil import parser
from prettytable import *

db_files = {
    'masa_default_btc': './data/crypto_trading.db',
    'masa_default_all_coins': './data2/crypto_trading.db'
}

CFG_FL_NAME = "./user.cfg"
USER_CFG_SECTION = "binance_user_config"
config = configparser.ConfigParser()
config.read(CFG_FL_NAME)

api_key = config.get(USER_CFG_SECTION, "api_key")
api_secret = config.get(USER_CFG_SECTION, "api_secret_key")
client = Client(api_key, api_secret)
'''
ENUM of transfer types:

MAIN_UMFUTURE Spot account transfer to USDⓈ-M Futures account
MAIN_CMFUTURE Spot account transfer to COIN-M Futures account
MAIN_MARGIN Spot account transfer to Margin（cross）account
UMFUTURE_MAIN USDⓈ-M Futures account transfer to Spot account
UMFUTURE_MARGIN USDⓈ-M Futures account transfer to Margin（cross）account
CMFUTURE_MAIN COIN-M Futures account transfer to Spot account
CMFUTURE_MARGIN COIN-M Futures account transfer to Margin(cross) account
MARGIN_MAIN Margin（cross）account transfer to Spot account
MARGIN_UMFUTURE Margin（cross）account transfer to USDⓈ-M Futures
MARGIN_CMFUTURE Margin（cross）account transfer to COIN-M Futures
ISOLATEDMARGIN_MARGIN Isolated margin account transfer to Margin(cross) account
MARGIN_ISOLATEDMARGIN Margin(cross) account transfer to Isolated margin account
ISOLATEDMARGIN_ISOLATEDMARGIN Isolated margin account transfer to Isolated margin account
MAIN_FUNDING Spot account transfer to Funding account
FUNDING_MAIN Funding account transfer to Spot account
FUNDING_UMFUTURE Funding account transfer to UMFUTURE account
UMFUTURE_FUNDING UMFUTURE account transfer to Funding account
MARGIN_FUNDING MARGIN account transfer to Funding account
FUNDING_MARGIN Funding account transfer to Margin account
FUNDING_CMFUTURE Funding account transfer to CMFUTURE account
CMFUTURE_FUNDING CMFUTURE account transfer to Funding account
'''
types = ["MAIN_UMFUTURE",
         "MAIN_CMFUTURE",
         "MAIN_MARGIN",
         "UMFUTURE_MAIN",
         "UMFUTURE_MARGIN",
         "CMFUTURE_MAIN",
         "CMFUTURE_MARGIN",
         "MARGIN_MAIN",
         "MARGIN_UMFUTURE",
         "MARGIN_CMFUTURE",
         "ISOLATEDMARGIN_MARGIN",
         "MARGIN_ISOLATEDMARGIN",
         "ISOLATEDMARGIN_ISOLATEDMARGIN",
         "MAIN_FUNDING",
         "FUNDING_MAIN",
         "FUNDING_UMFUTURE",
         "UMFUTURE_FUNDING",
         "MARGIN_FUNDING",
         "FUNDING_MARGIN",
         "FUNDING_CMFUTURE",
         "CMFUTURE_FUNDING", ]
now = datetime.utcnow()
start_time = now - timedelta(days=6 * 30)
start_time = int(time.mktime(start_time.timetuple()) * 1000)
ins = 0
outs = 0
for t in types:
    if 'MAIN' in t:
        transfers = client.query_universal_transfer_history(type=t, startTime=start_time, size=100)
        t_split = t.split('_')
        in_or_out = 'OUT' if 'MAIN' == t_split[0] else 'IN'
        if int(transfers['total']) > 0:
            for transfer in transfers['rows']:
                if transfer['status'] == 'CONFIRMED':
                    if in_or_out == 'OUT':
                        outs += float(transfer['amount'])
                    if in_or_out == 'IN':
                        ins += float(transfer['amount'])

total_spot_value = ins - outs


# funding_to_spot = client.query_universal_transfer_history(type='FUNDING_MAIN', startTime=start_time, size=100)
# future_to_spot = client.query_universal_transfer_history(type='UMFUTURE_MAIN', startTime=start_time, size=100)


def get_balance_at_time(coin_balances, coin, timestamp):
    coin_balance = coin_balances[coin]
    closest = time.time()
    for b in coin_balance:
        diff = timestamp - b['time']
        diff_sec = abs(diff.total_seconds())
        if diff_sec < closest:
            result = b
            closest = diff_sec
    return result


first_trade = None
traded_coins = set()
for key in db_files:
    # list all traded coins so far
    DB_FILE = db_files[key]  # './data/crypto_trading.db'
    cursor = sqlite3.connect(DB_FILE)
    db = cursor.cursor()

    db.execute('SELECT coin_id from main.current_coin_history order by id asc')
    result = db.fetchall()

    for r in result:
        traded_coins.add(r[0])

    db.execute('SELECT datetime from main.current_coin_history order by id asc LIMIT 1')
    result = db.fetchall()
    ft = parser.parse(result[0][0])
    timezone = pytz.timezone("UTC")
    ft = timezone.localize(ft)
    if first_trade is None or ft < first_trade:
        first_trade = ft

## get balance histoy
balances = {}
for coin in traded_coins:
    trades_for_coin = client.get_my_trades(symbol=f'{coin}USDT')
    trades_for_coin.sort(key=lambda x: x['time'], reverse=False)
    coin_history = []
    current_balance = 0
    current_balance_usdt = 0
    for trade in trades_for_coin:
        timestamp = datetime.fromtimestamp(trade['time'] / 1000)
        timestamp = timestamp.astimezone(pytz.timezone('UTC'))
        is_buy = trade['isBuyer']
        coin_amount = float(trade['qty'])
        price_in_usdt = float(trade['price'])
        if current_balance == 0:
            current_balance = coin_amount
        else:
            if is_buy:
                current_balance += coin_amount
            else:
                current_balance -= coin_amount
        current_balance_usdt = current_balance * price_in_usdt
        coin_history.append({
            'time': timestamp,
            'action': 'BUY' if is_buy else 'SELL',
            'coin_amount': coin_amount,
            'price_in_usdt': price_in_usdt,
            'balance': current_balance,
            'value_in_usdt': current_balance_usdt
        })
    print(f'Final balance for {coin} is {coin_history[-1]["balance"]}')
    balances[coin] = coin_history

## now iterate for all traded_coins to get balance at the beginning of trade and now

growth = {}

total_starting_value = 0
total_finish_value = 0
for coin in traded_coins:
    coin_held_at_beginning = get_balance_at_time(balances, coin, first_trade)

    coin_held_now = client.get_asset_balance(asset=coin)
    coin_held_now['coin_amount'] = float(coin_held_now['free']) + float(coin_held_now['locked'])
    price_url = f"https://api.binance.com/api/v3/ticker/price?symbol={coin}USDT"
    current_price = float(requests.get(price_url).json()['price'])
    current_value = coin_held_now['coin_amount'] * current_price

    total_starting_value += coin_held_at_beginning['value_in_usdt']
    total_finish_value += current_value

    growth[coin] = {
        'start_coin': coin_held_at_beginning['coin_amount'],
        'start_value': coin_held_at_beginning['value_in_usdt'],
        'end_coin': coin_held_now['coin_amount'],
        'end_value': current_value
    }

print('\n:: Coin progress ::')
msg = PrettyTable()
msg.field_names = ["Coin", "From", "To", "Growth", "From Value (USDT)", "To Value(USDT)"]
for coin in growth:
    g = growth[coin]
    increase = ((g['end_coin'] - g['start_coin']) / g['start_coin']) * 100
    msg.add_row([coin,
                 '{:.2f}'.format(g['start_coin']),
                 '{:.2f}'.format(g['end_coin']),
                 '{:.4f}%'.format(increase),
                 '{:.2f}'.format(g['start_value']),
                 '{:.2f}'.format(g['end_value']),
                 ])

msg.align = "l"
print(msg)
print(f'total_invested:{total_spot_value}'
      f'total_starting_value : {total_starting_value} ->> total_finish_value: {total_finish_value}')
print('\n--------------------\n')

'''




'''