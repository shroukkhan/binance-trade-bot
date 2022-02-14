import json
import sqlite3
from datetime import datetime, timedelta

from prettytable import *

from binance_trade_bot import backtest
from binance_trade_bot import config


def print_progress(current: float, total: float, avg: float):
    progress = round((current / total) * 100, 2)
    ms_left = (total - current) * avg
    will_finish_at = datetime.now() + timedelta(milliseconds=ms_left)
    print(f'progress: {progress}% of {total} iterations, ETA:{will_finish_at} (avg_ms: {avg}, ms_left: {ms_left})')


def show_jumps(c: config.Config, starting_coin: str, starting_balance: dict, filename: str):
    db_file = f'.{filename}'  # './data/crypto_trading.db'
    cursor = sqlite3.connect(db_file)

    db = cursor.cursor()

    db.execute('SELECT datetime FROM trade_history where selling=0 and state=\'COMPLETE\' order by id asc limit 1')
    bot_start_date = db.fetchall()[0][0]

    db.execute('SELECT datetime FROM scout_history order by id desc limit 1')
    bot_end_date = db.fetchall()[0][0]

    db.execute('SELECT alt_coin_id FROM trade_history where id=1 and state=\'COMPLETE\' order by id asc limit 1')
    initialCoinID = db.fetchall()[0][0]

    db.execute('select alt_trade_amount from trade_history where id=1 and state=\'COMPLETE\' order by id asc limit 1')
    initialCoinValue = db.fetchall()[0][0]

    db.execute(
        'select crypto_trade_amount from trade_history where id=1 and state=\'COMPLETE\' order by id asc limit 1')
    initialCoinFiatValue = db.fetchall()[0][0]

    db.execute('select alt_coin_id from trade_history where selling=0 and state=\'COMPLETE\' order by id desc limit 1')
    lastCoinID = db.fetchall()[0][0]

    db.execute(
        'select alt_trade_amount from trade_history where selling=0 and state=\'COMPLETE\' order by id desc limit 1')
    lastCoinValue = db.fetchall()[0][0]

    db.execute('select current_coin_price from scout_history order by rowid desc limit 1')
    lastCoinUSD = db.fetchall()[0][0]

    lastCoinFiatValue = lastCoinValue * lastCoinUSD

    if lastCoinID != initialCoinID:
        db.execute(
            "select id from pairs where from_coin_id=\'{}\' and to_coin_id=\'{}\'".format(lastCoinID, initialCoinID))
        pairID = db.fetchall()[0][0]
        db.execute(
            "select other_coin_price from scout_history where pair_id=\'{}\' order by id desc limit 1".format(pairID))
        currentValInitialCoin = db.fetchall()[0][0]
    else:
        db.execute("select current_coin_price from scout_history order by id desc limit 1")
        currentValInitialCoin = lastCoinUSD

    imgStartCoinFiatValue = initialCoinValue * currentValInitialCoin
    imgStartCoinValue = lastCoinFiatValue / currentValInitialCoin
    imgPercChangeCoin = (imgStartCoinValue - initialCoinValue) / initialCoinValue * 100

    percChangeFiat = (lastCoinFiatValue - imgStartCoinFiatValue) / imgStartCoinFiatValue * 100

    # No of Days calculation
    start_date = datetime.strptime(bot_start_date[2:], '%y-%m-%d %H:%M:%S.%f')
    end_date = datetime.strptime(bot_end_date[2:], '%y-%m-%d %H:%M:%S.%f')
    numDays = (end_date - start_date).days
    if numDays == 0:
        numDays = 1

    db.execute('select count(*) from trade_history where selling=0')
    numCoinJumps = db.fetchall()[0][0]

    msg = f'Stat for bot     : {filename}'
    msg += '\nBot Started    : {}'.format(start_date.strftime("%m/%d/%Y, %H:%M:%S"))
    msg += '\nBot Ended      : {}'.format(end_date.strftime("%m/%d/%Y, %H:%M:%S"))
    msg += '\nNo of Days     : {}'.format(numDays)
    msg += '\nCoins          : {}'.format(','.join(c.SUPPORTED_COIN_LIST))
    msg += '\nStrategy       : {}'.format(c.STRATEGY)
    msg += '\nStart Coin     : {}'.format(starting_coin)
    msg += '\nStart Balance  : {}'.format(str(starting_balance))
    msg += '\nUsing margin?  : {}'.format(c.USE_MARGIN)
    msg += '\nScout Margin   : {}'.format(c.SCOUT_MARGIN)
    msg += '\nNo of Jumps    : {} ({:.1f} jumps/day)'.format(numCoinJumps, numCoinJumps / numDays)
    msg += '\nStart Coin     : {:.4f} {} <==> ${:.3f}'.format(initialCoinValue, initialCoinID, initialCoinFiatValue)
    msg += '\nCurrent Coin   : {:.4f} {} <==> ${:.3f}'.format(lastCoinValue, lastCoinID, lastCoinFiatValue)
    msg += '\nHODL           : {:.4f} {} <==> ${:.3f}'.format(initialCoinValue, initialCoinID, imgStartCoinFiatValue)
    msg += '\n\nApprox Profit: {:.2f}% in USD'.format(percChangeFiat)

    if lastCoinID != initialCoinID:
        msg += '\n{} can be approx converted to {:.2f} {}'.format(lastCoinID, imgStartCoinValue, initialCoinID)

    # print(msg)

    db.execute('select symbol from coins where enabled=1')
    coinList = db.fetchall()  # access with coinList[Index][0]
    numCoins = len(coinList)

    msg += '\n:: Coin progress ::\n'
    x = PrettyTable()
    x.field_names = ["Coin", "From", "To", "%+-", "<->"]

    multiTrades = 0
    # Compute Mini Coin Progress
    for coin in coinList:
        jumps = db.execute(
            f"select count(*) from trade_history where alt_coin_id=\'{coin[0]}\' and selling=0 and state=\'COMPLETE\'").fetchall()[
            0][0]
        if jumps > 0:
            multiTrades += jumps
            first_date = db.execute(
                f'select datetime from trade_history where alt_coin_id=\'{coin[0]}\' and selling=0 and state=\'COMPLETE\' order by id asc limit 1').fetchall()[
                0][0]
            first_value = db.execute(
                f'select alt_trade_amount from trade_history where alt_coin_id=\'{coin[0]}\' and selling=0 and state=\'COMPLETE\' order by id asc limit 1').fetchall()[
                0][0]
            last_value = db.execute(
                f'select alt_trade_amount from trade_history where alt_coin_id=\'{coin[0]}\' and selling=0 and state=\'COMPLETE\' order by id desc limit 1').fetchall()[
                0][0]
            grow = (last_value - first_value) / first_value * 100
            x.add_row([coin[0], '{:.2f}'.format(first_value), '{:.2f}'.format(last_value), '{:.1f}'.format(grow),
                       '{}'.format(jumps)])

    x.align = "l"

    msg += x.get_string()

    print(msg)
    print('\n--------------------\n')
    return msg


if __name__ == "__main__":

    history = []
    start_date = datetime(year=2021,
                          month=5,
                          day=15,
                          hour=0,
                          minute=0)

    # end_date = datetime.now()
    end_date = datetime(year=2021,
                        month=5,
                        day=15,
                        hour=23,
                        minute=0)

    c = config.Config()
    c.SUPPORTED_COIN_LIST = list(dict.fromkeys([
        'FIL',
        'AAVE',
        'VET',
        'ETH',
        'GRT',
        'LINK',
        'ALGO',
        'DOT',
        'SOL',
        'EOS',
        'UNI',
        'FTT',
        'BTC',
        'FTM',
        'NEAR',
        'ICP',
        'MATIC',
        'LTC',
        'ONE',
        'ADA',
        'DOGE',
        'BCH',
        'TRX',
        'CAKE',
        'IOTA',
        'BTC',
        'ETH',
        'ADA',
        'SOL',
        'XRP',
        'DOT',
        'LINK',
        'UNI',
        'LTC',
        'ALGO'
    ]))
    # c.SUPPORTED_COIN_LIST = [
    #     'BTC',
    #     'ETH',
    #     'ADA',
    #     'SOL',
    #     'XRP',
    #     'DOT',
    #     'LINK',
    #     'UNI',
    #     'LTC',
    #     'ALGO'
    # ]
    c.USE_MARGIN = True
    c.STRATEGY = 'multiple_coins'
    c.SCOUT_MARGIN = 0.65
    starting_coin = 'SOL'
    starting_balance = {'USDT': 0, 'SOL': 1.72, 'FIL': 8.1, 'BTC': 0.0023, 'ETH': 0.178, 'BNB': 0.05314571,
                        'SOLO': 0.27060350}



    if starting_coin not in c.SUPPORTED_COIN_LIST:
        raise Exception(f'Coin {starting_coin} not in c.SUPPORTED_COIN_LIST')

    length = end_date - start_date
    print(f'Testing for : {length.days} days')

    total_minutes = length.total_seconds() / 60

    result = {}
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backtest_file = f'./backtest_results/backtest-{timestamp}.json'
    result_file = f'./backtest_results/backtest-{timestamp}.txt'

    # msg = show_jumps(c=c, starting_coin=starting_coin, starting_balance=starting_balance,
    #                  filename='/backtest_results/backtest-20220213-222603.db')
    #
    # with open(result_file, "w") as f:
    #     f.writelines(msg)
    # exit(1)


    __sqlite_db = f'/backtest_results/backtest-{timestamp}.db'
    backtest_database = f'sqlite://{__sqlite_db}'

    # coins = list(line.strip() for line in open('./supported_coin_list'))
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
        btc_value = manager.collate_coins("BTC")
        bridge_value = manager.collate_coins(manager.config.BRIDGE.symbol)
        history.append((btc_value, bridge_value))
        btc_diff = round((btc_value - history[0][0]) / history[0][0] * 100, 3)
        bridge_diff = round((bridge_value - history[0][1]) / history[0][1] * 100, 3)

        # print("------")
        # print("TIME:", manager.datetime)
        # print("BALANCES:", manager.balances)
        # print("BTC VALUE:", btc_value, f"({btc_diff}%)")
        # print(f"{manager.config.BRIDGE.symbol} VALUE:", bridge_value, f"({bridge_diff}%)")
        # print("------")

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
        iteration_left = (start_date - manager.datetime).total_seconds() / 60
        now = datetime.now()
        average_per_iteration = ((now - iteration_start_at).total_seconds() * 1000) / total_iteration_so_far

        # pbar.update(progress)
        print_progress(total_iteration_so_far, total_minutes, average_per_iteration)

    with open(backtest_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    #show_jumps(__sqlite_db)
    msg = show_jumps(c=c, starting_coin=starting_coin, starting_balance=starting_balance,
                     filename=__sqlite_db)

    with open(result_file, "w") as f:
        f.writelines(msg)
