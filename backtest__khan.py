import json
import sqlite3
from datetime import datetime
from datetime import timedelta

from binance.client import Client
from prettytable import *

from binance_trade_bot import backtest
from binance_trade_bot import config


def print_progress(current: float, total: float, avg: float, now: datetime, target: datetime):
    progress = round((current / total) * 100, 2)
    ms_left = (total - current) * avg
    will_finish_at = datetime.now() + timedelta(milliseconds=ms_left)
    print(
        f'progress: {progress}% of {total} iterations, '
        f'ETA:{will_finish_at} '
        f'( avg_ms: {avg}, ms_left: {ms_left}, now:{now.strftime("%y-%m-%d %H:%M:%S.%f")}, '
        f'target: {target.strftime("%y-%m-%d %H:%M:%S.%f")} )')


def get_account_balance(client: Client, coins: []):
    result = {}
    for coin in coins:
        asset_balance = client.get_asset_balance(asset=coin)
        result[coin] = float(asset_balance['free']) + float(asset_balance['locked'])
    return result


if __name__ == "__main__":

    history = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=120)
    starting_coin = 'SOL'

    c = config.Config()
    api_key = c.BINANCE_API_KEY
    api_secret = c.BINANCE_API_SECRET_KEY
    client = Client(api_key, api_secret)
    c.SUPPORTED_COIN_LIST = list(line.strip() for line in open('./supported_coin_list'))

    starting_balance = get_account_balance(client, c.SUPPORTED_COIN_LIST)
    print(f'Starting balance : {starting_balance}')
    starting_balance_copy = starting_balance.copy()

    if starting_coin != '' and starting_coin not in c.SUPPORTED_COIN_LIST:
        raise Exception(f'Coin {starting_coin} not in c.SUPPORTED_COIN_LIST')

    length = end_date - start_date
    print(f'Testing for : {length.days} days')

    total_minutes = length.total_seconds() / 60

    result = {}
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backtest_file = f'./backtest_results/backtest-{timestamp}.json'
    result_file = f'./backtest_results/backtest-{timestamp}'

    __sqlite_db = f'/backtest_results/backtest-{timestamp}.db'
    backtest_database = f'sqlite://{__sqlite_db}'

    result['coins'] = c.SUPPORTED_COIN_LIST
    result['full_data'] = {}
    result['balance'] = []
    result['btc_value'] = []
    result['usdt_value'] = []

    iteration_start_at = datetime.now()

    for manager in backtest(start_date=start_date,
                            end_date=end_date,
                            start_balances=starting_balance,
                            starting_coin=starting_coin,
                            config=c,
                            backtest_db_url=backtest_database
                            ):



        b = manager.balances
        btc_value = manager.collate_coins("BTC")
        bridge_value = manager.collate_coins(manager.config.BRIDGE.symbol)
        history.append((btc_value, bridge_value))
        btc_diff = round((btc_value - history[0][0]) / history[0][0] * 100, 3)
        bridge_diff = round((bridge_value - history[0][1]) / history[0][1] * 100, 3)

        result['full_data'][manager.datetime.strftime("%Y-%m-%d %H:%M:%S")] = {
            'balance': manager.balances,
            'btc': {'value': btc_value, 'diff': btc_diff},
            manager.config.BRIDGE.symbol: {'value': bridge_value, 'diff': bridge_diff},
        }

        result['balance'].append({
            'date': manager.datetime.strftime("%Y-%m-%d %H:%M:%S"),
            **manager.balances
        })
        result['btc_value'].append({
            'date': manager.datetime.strftime("%Y-%m-%d %H:%M:%S"),
            'value': btc_value, 'diff': btc_diff
        })
        result['usdt_value'].append({
            'date': manager.datetime.strftime("%Y-%m-%d %H:%M:%S"),
            'value': bridge_value, 'diff': bridge_diff
        })

        total_iteration_so_far = max(1, (manager.datetime - start_date).total_seconds() / 60)
        now = datetime.now()
        average_per_iteration = ((now - iteration_start_at).total_seconds() * 1000) / total_iteration_so_far

        print_progress(total_iteration_so_far, total_minutes, average_per_iteration, manager.datetime, end_date)

    with open(backtest_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
