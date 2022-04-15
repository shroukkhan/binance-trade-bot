import configparser
import sqlite3
import time
from datetime import datetime

import pytz
from binance.client import Client
from dateutil import parser
from prettytable import *

df_file = './data/crypto_trading.db'
# db_files = {
#     'masa_default_btc': './data/crypto_trading.db',
#     'masa_default_all_coins': './data2/crypto_trading.db'
# }

CFG_FL_NAME = "./user.cfg"
USER_CFG_SECTION = "binance_user_config"
config = configparser.ConfigParser()
config.read(CFG_FL_NAME)

api_key = config.get(USER_CFG_SECTION, "api_key")
api_secret = config.get(USER_CFG_SECTION, "api_secret_key")
client = Client(api_key, api_secret)


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


def get_coin_holding_time(dbfile, coin):
    cursor = sqlite3.connect(dbfile)
    db = cursor.cursor()

    db.execute(
        'SELECT datetime from main.trade_history where alt_coin_id = ? and selling = ? order by datetime asc',
        (coin, 0))
    result = db.fetchall()
    db.close()


def get_all_buy_trades(dbfile, coin):
    cursor = sqlite3.connect(dbfile)
    db = cursor.cursor()
    db.execute(
        'SELECT datetime from main.trade_history where alt_coin_id = ? and selling = ? order by datetime asc',
        (coin, 0))
    result = db.fetchall()
    buy_times = []
    timezone = pytz.timezone("UTC")
    for d in result:
        buy_time = parser.parse(d[0])
        buy_time = timezone.localize(buy_time)
        buy_times.append(buy_time)

    db.close()
    return buy_times


def get_coin_balances(coin):
    balances = {}
    trades_for_coin = client.get_my_trades(symbol=f'{coin}USDT')
    trades_for_coin.sort(key=lambda x: x['time'], reverse=False)
    coin_history = []
    current_balance = 0
    current_balance_usdt = 0
    msg = PrettyTable()
    msg.field_names = ["Date", "Action", "From", "Amount", "Kept Pct", "Final Balance"]
    for trade in trades_for_coin:
        timestamp = datetime.fromtimestamp(trade['time'] / 1000)
        timestamp = timestamp.astimezone(pytz.timezone('UTC'))
        is_buy = trade['isBuyer']
        coin_amount = float(trade['qty'])
        price_in_usdt = float(trade['price'])
        initial = current_balance
        if is_buy:
            pct = 0
            current_balance += coin_amount
        else:
            pct = ((current_balance - coin_amount) / current_balance) * 100
            current_balance -= coin_amount

        current_balance_usdt = current_balance * price_in_usdt
        msg.add_row([
            timestamp,
            'Buy' if is_buy else 'Sell',
            '{:.2f}'.format(float(initial)),
            '{:.2f}'.format(float(coin_amount)),
            '{:.2f}'.format(float(pct)),
            '{:.2f}'.format(float(current_balance)),
        ])
        coin_history.append({
            'time': timestamp,
            'action': 'BUY' if is_buy else 'SELL',
            'coin_amount': coin_amount,
            'price_in_usdt': price_in_usdt,
            'balance': current_balance,
            'value_in_usdt': current_balance_usdt
        })

    msg.align = "l"
    print(msg)
    print(f'Final balance for {coin} is {coin_history[-1]["balance"]}')
    print('------------------------------------------------------------')
    balances[coin] = coin_history
    return balances


traded_coins = ['ATOM','LUNA']
growth = {}
total_starting_value = 0
total_finish_value = 0
for coin in traded_coins:
    print(f"==== ===== ======= ======= ===={coin}===== ======= ========== ======== ======")
    trades = get_all_buy_trades(df_file, coin)
    balances = get_coin_balances(coin)

    for t in trades:
        coin_held = get_balance_at_time(balances, coin, t)
        print(f'@{t} -> {coin_held["coin_amount"]}')

    #     growth[coin] = {
    #         'start_coin': coin_held_at_beginning['coin_amount'],
    #         'start_value': coin_held_at_beginning['value_in_usdt'],
    #         'end_coin': coin_held_now['coin_amount'],
    #         'end_value': current_value
    #     }
    # first_trade = trades[0]
    #
    #
    #
    # coin_hel = client.get_asset_balance(asset=coin)
    # coin_held_now['coin_amount'] = float(coin_held_now['free']) + float(coin_held_now['locked'])
    # price_url = f"https://api.binance.com/api/v3/ticker/price?symbol={coin}USDT"
    # current_price = float(requests.get(price_url).json()['price'])
    # current_value = coin_held_now['coin_amount'] * current_price
    #
    # total_starting_value += coin_held_at_beginning['value_in_usdt']
    # total_finish_value += current_value

# print('\n:: Coin progress ::')
# msg = PrettyTable()
# msg.field_names = ["Coin", "From", "To", "Growth", "From Value (USDT)", "To Value(USDT)"]
# for coin in growth:
#     g = growth[coin]
#     increase = ((g['end_coin'] - g['start_coin']) / g['start_coin']) * 100
#     msg.add_row([coin,
#                  '{:.2f}'.format(g['start_coin']),
#                  '{:.2f}'.format(g['end_coin']),
#                  '{:.4f}%'.format(increase),
#                  '{:.2f}'.format(g['start_value']),
#                  '{:.2f}'.format(g['end_value']),
#                  ])
#
# msg.align = "l"
# print(msg)
# print(f'total_invested:{total_spot_value}'
#       f'total_starting_value : {total_starting_value} ->> total_finish_value: {total_finish_value}')
# print('\n--------------------\n')
