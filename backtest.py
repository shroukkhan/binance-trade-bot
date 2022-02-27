import json
import sqlite3
from datetime import datetime, timedelta

from prettytable import *
from sqlitedict import SqliteDict

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

def show_jumps(c: config.Config,
               starting_coin: str,
               starting_balance: dict,
               current_balance: dict, filename: str,
               starting_date: datetime, ending_date: datetime,
               manager):
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

    initial_total_value = 0
    for k, v in starting_balance.items():
        initial_total_value += v * manager.get_ticker_price_on_date(k + 'USDT', starting_date)

    final_total_value = 0
    for k, v in current_balance.items():
        final_total_value += v * manager.get_ticker_price_on_date(k + 'USDT', ending_date)

    msg = f'Stat for bot     : {filename}'
    msg += '\nBot Started    : {}'.format(start_date.strftime("%m/%d/%Y, %H:%M:%S"))
    msg += '\nBot Ended      : {}'.format(end_date.strftime("%m/%d/%Y, %H:%M:%S"))
    msg += '\nNo of Days     : {}'.format(numDays)
    msg += '\nCoins          : {}'.format(','.join(c.SUPPORTED_COIN_LIST))
    msg += '\nStrategy       : {}'.format(c.STRATEGY)
    msg += '\nUsing Wiggle   : {}'.format(str(c.USE_WIGGLE))
    msg += '\nWiggle Factor  : {}'.format(c.WIGGLE_FACTOR)
    msg += '\nStart Coin     : {}'.format(starting_coin)
    msg += '\nStart Balance  : {}'.format(str(starting_balance))
    msg += '\nStart Balance Value: {}'.format(initial_total_value)
    msg += '\nFinal Balance  : {}'.format(str(current_balance))
    #msg += '\nFinal Balance Value: {}'.format(final_total_value)
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
                          month=7,
                          day=26,
                          hour=0,
                          minute=0)

    end_date = datetime.now()
    # end_date = datetime(year=2021,
    #                     month=5,
    #                     day=15,
    #                     hour=23,
    #                     minute=0)

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
        'ALGO',
        'BNB'
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
    c.STRATEGY = 'default'
    c.USE_WIGGLE = True
    # c.COINS_TO_GAIN = []
    c.SCOUT_MARGIN = 0.7
    starting_coin = ''
    starting_balance = {'USDT': 500}

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
        s = datetime(year=2021,
                              month=7,
                              day=26,
                              hour=0,
                              minute=0)
        e = datetime(year=2022,
                            month=2,
                            day=27,
                            hour=13,
                            minute=44)
        msg = show_jumps(c=c,
                         starting_coin=starting_coin,
                         starting_balance=starting_balance,
                         current_balance={'USDT': 0.0747196558000951, 'FIL': 36.61073, 'NEAR': 375.6201000000001, 'ALGO': 561.9879999999998, 'ICP': 6.753369999999997, 'SOL': 28.681140000000013, 'ONE': 5953.387699999999, 'BTC': 0.010958480000000007, 'AAVE': 0.8490259999999994, 'IOTA': 338.307, 'LTC': 1.6736239999999993, 'BCH': 0.3791040000000001, 'EOS': 61.43900000000005, 'DOGE': 1149.3980000000001},
                         filename='/backtest_results/backtest-20220227-175944.db',
                         starting_date=s, ending_date=e , manager=manager)

        with open(result_file, "w") as f:
            f.writelines(msg)
        exit(1)

        b = manager.balances
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
        # iteration_left = (end_date - manager.datetime).total_seconds() / 60
        now = datetime.now()
        average_per_iteration = ((now - iteration_start_at).total_seconds() * 1000) / total_iteration_so_far

        # pbar.update(progress)
        print_progress(total_iteration_so_far, total_minutes, average_per_iteration, manager.datetime, end_date)

    with open(backtest_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    # show_jumps(__sqlite_db)
    msg = show_jumps(c=c,
                     starting_coin=starting_coin,
                     starting_balance=starting_balance_copy,
                     current_balance=manager.balances,
                     starting_date=start_date,
                     ending_date=end_date,
                     manager=manager,
                     filename=__sqlite_db)

    with open(result_file, "w") as f:
        f.writelines(msg)
