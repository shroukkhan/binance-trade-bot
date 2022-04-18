import sqlite3
from datetime import datetime

from prettytable import *

db_files = {
   'Btc based': './data/crypto_trading.db',
    'Shit based': './data1/crypto_trading.db'
}

coin_lists = {
    'Btc based': './supported_coin_list',
    'Shit based': './supported_coin_list1'
}

for key in db_files:
    title = key
    coins = set(line.strip() for line in open(coin_lists[key]))

    DB_FILE = db_files[key]  # './data/crypto_trading.db'
    cursor = sqlite3.connect(DB_FILE)

    db = cursor.cursor()

    db.execute('SELECT alt_coin_id, datetime FROM trade_history where selling=0 and state=\'COMPLETE\' order by id asc')
    result = db.fetchall()
    for r in result:
        if r[0] in coins:
            bot_start_date = r[1]
            break

    db.execute('SELECT datetime FROM scout_history order by id desc limit 1')
    bot_end_date = db.fetchall()[0][0]

    db.execute('SELECT alt_coin_id FROM trade_history where state=\'COMPLETE\' order by id asc')
    result = db.fetchall()
    for r in result:
        if r[0] in coins:
            initialCoinID = r[0]
            break

    db.execute('select alt_coin_id, alt_trade_amount from trade_history where state=\'COMPLETE\' order by id asc')
    result = db.fetchall()
    for r in result:
        if r[0] in coins:
            initialCoinValue = r[1]
            break

    db.execute(
        'select alt_coin_id, crypto_trade_amount from trade_history where state=\'COMPLETE\' order by id asc')
    result = db.fetchall()
    for r in result:
        if r[0] in coins:
            initialCoinFiatValue = r[1]
            break
    #initialCoinFiatValue = db.fetchall()[0][0]

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

    msg = f'Stat for bot : {key}'
    msg += 'Bot Started  : {}'.format(start_date.strftime("%m/%d/%Y, %H:%M:%S"))
    msg += '\nNo of Days   : {}'.format(numDays)
    msg += '\nNo of Jumps  : {} ({:.1f} jumps/day)'.format(numCoinJumps, numCoinJumps / numDays)
    msg += '\nStart Coin   : {:.4f} {} <==> ${:.3f}'.format(initialCoinValue, initialCoinID, initialCoinFiatValue)
    msg += '\nCurrent Coin : {:.4f} {} <==> ${:.3f}'.format(lastCoinValue, lastCoinID, lastCoinFiatValue)
    msg += '\nHODL         : {:.4f} {} <==> ${:.3f}'.format(initialCoinValue, initialCoinID, imgStartCoinFiatValue)
    msg += '\n\nApprox Profit: {:.2f}% in USD'.format(percChangeFiat)

    if lastCoinID != initialCoinID:
        msg += '\n{} can be approx converted to {:.2f} {}'.format(lastCoinID, imgStartCoinValue, initialCoinID)

    print(msg)

    db.execute('select symbol from coins where enabled=1')
    coinList = db.fetchall()  # access with coinList[Index][0]
    numCoins = len(coinList)

    print('\n:: Coin progress ::')
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
    print(x)
    print('\n--------------------\n')
