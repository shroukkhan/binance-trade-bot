import pytest

import os, datetime
from typing import Dict, List

from binance.client import Client
from sqlitedict import SqliteDict

from binance_trade_bot.auto_trader import AutoTrader
from binance_trade_bot.backtest import MockBinanceManager

from binance_trade_bot.binance_stream_manager import BinanceCache
from binance_trade_bot.config import Config
from binance_trade_bot.database import Database
from binance_trade_bot.logger import Logger
from binance_trade_bot.ratios import CoinStub

from .common import infra, dmlc


@pytest.fixture(scope='function')
def DoUserConfig():
    '''
    CURRENT_COIN_SYMBOL:
    SUPPORTED_COIN_LIST: "XLM TRX ICX EOS IOTA ONT QTUM ETC ADA XMR DASH NEO ATOM DOGE VET BAT OMG BTT"
    BRIDGE_SYMBOL: USDT
    API_KEY: vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A
    API_SECRET_KEY: NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j
    SCOUT_MULTIPLIER: 5
    SCOUT_SLEEP_TIME: 1
    TLD: com
    STRATEGY: default
    BUY_TIMEOUT: 0
    SELL_TIMEOUT: 0
    BUY_ORDER_TYPE: limit
    SELL_ORDER_TYPE: market
    '''

    # os.environ['CURRENT_COIN'] = 'ETH'
    os.environ['CURRENT_COIN_SYMBOL'] = 'ETH'

    os.environ['API_KEY'] = 'vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A'
    os.environ['API_SECRET_KEY'] = 'NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j'

    # os.environ['CURRENT_COIN_SYMBOL'] = 'BTT'
    os.environ['SUPPORTED_COIN_LIST'] = "XLM TRX ICX EOS IOTA ONT QTUM ETC ADA XMR DASH NEO ATOM DOGE VET BAT OMG BTT"
    os.environ['BRIDGE_SYMBOL'] = "USDT"
    os.environ['SCOUT_MULTIPLIER'] = "5"
    os.environ['SCOUT_SLEEP_TIME'] = "1"
    os.environ['TLD'] = 'com'
    os.environ['STRATEGY'] = 'default'
    os.environ['BUY_TIMEOUT'] = "0"
    os.environ['SELL_TIMEOUT'] = "0"
    os.environ['BUY_ORDER_TYPE'] = 'limit'
    os.environ['SELL_ORDER_TYPE'] = 'market'

    yield

@pytest.fixture()
def mmbm():

    logger: Logger = Logger(logging_service="guliguli")
    config: Config = Config()
    sqlite_cache = SqliteDict("data/testtest_cache.db")

    db = Database(logger, config)
    db.create_database()
    db.set_coins(config.SUPPORTED_COIN_LIST)

    start_date: datetime = datetime.datetime(2021, 6, 1)
    start_balances: Dict[str, float] = dict()
    #start_balances['BAD']  = None
    #start_balances['BAD'] = 10300000
    start_balances['XLM'] = 100
    start_balances['DOGE'] = 101
    start_balances['BTT'] = 102
    start_balances['USDT'] = 1000

    manager = MockBinanceManager(
        Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET_KEY, tld=config.BINANCE_TLD),
        sqlite_cache,
        BinanceCache(),
        config,
        db,
        logger,
        start_date,
        start_balances,
    )

    yield db, manager, logger, config

    #manager.close()
    #db.close()
    sqlite_cache.close()

class StubAutoTrader(AutoTrader) :
    def scout(self):
        return

class TestAutoTrader:

    def test_initialize(self, DoUserConfig, mmbm):
        # test on run
        db, manager, logger, config = mmbm
        autotrader = StubAutoTrader(manager, db, logger, config)
        autotrader.initialize()
        assert True

    # TODO: Check infinity loop probably
    def test_transaction_through_bridge(self, DoUserConfig, mmbm):
        # test on run
        db, manager, logger, config = mmbm

        autotrader = StubAutoTrader(manager, db, logger, config)

        coinfrom = CoinStub.get_by_symbol('XLM')
        cointo = CoinStub.get_by_symbol('EOS')

        sell_price = autotrader.manager.get_ticker_price('XLMUSDT')
        buy_price  = autotrader.manager.get_ticker_price('EOSUSDT')

        autotrader.transaction_through_bridge(coinfrom, cointo, sell_price, buy_price)
        assert True

    # TODO: Check set matrix + breaks
    @pytest.mark.parametrize("coin_symbol",['XLM', 'DOGE'])
    def test_update_trade_threshold(self, DoUserConfig, mmbm, coin_symbol):

        # test on run
        db, manager, logger, config = mmbm

        autotrader = StubAutoTrader(manager, db, logger, config)

        coin = CoinStub.get_by_symbol(coin_symbol)
        res = autotrader.update_trade_threshold(coin, None, 100)
        assert not res

        coin = CoinStub.get_by_symbol('XLM')
        res = autotrader.update_trade_threshold(coin, 1000, 100)
        assert res

    # TODO: Why time.sleep(1)?
    # TODO: balanses[XXX] = None ! -1
    def test__max_value_in_wallet(self, DoUserConfig, mmbm):
        # test on run
        db, manager, logger, config = mmbm

        autotrader = StubAutoTrader(manager, db, logger, config)
        res = autotrader._max_value_in_wallet()
        print(f'_wallet {res}')
        assert True

        #bridge_balance = autotrader.manager.get_currency_balance(autotrade.config.BRIDGE.symbol)
        #assert res == bridge_balance

    def test_initialize_trade_thresholds(self, DoUserConfig, mmbm):

        # test on run
        db, manager, logger, config = mmbm

        autotrader = StubAutoTrader(manager, db, logger, config)
        res = autotrader.initialize_trade_thresholds()
        assert True

    def test_scout(self, DoUserConfig, mmbm):

        # test on run
        db, manager, logger, config = mmbm

        autotrader = StubAutoTrader(manager, db, logger, config)
        autotrader.scout()
        assert True

    @pytest.mark.parametrize("coin_symbol",['XLM', 'DOGE'])
    def test__get_ratios(self, DoUserConfig, mmbm, coin_symbol):
        # test on run
        db, manager, logger, config = mmbm

        coin = CoinStub.get_by_symbol(coin_symbol)
        autotrader = StubAutoTrader(manager, db, logger, config)

        ratio_dict, price_amounts = autotrader._get_ratios(coin, 100, 100)
        #print('\n_get_ratios:', ratio_dict, '\n', price_amounts)
        assert True

        # test on calculation. Calculate on first free coin (to_coin).

        to_coin = CoinStub.get_by_idx(0 if coin.idx != 0 else 1)

        ## Initial values for assert. Sell price & ratio
        quote_amount = 10000
        coin_sell_price = autotrader.manager.get_ticker_price(coin.symbol + autotrader.config.BRIDGE.symbol)
        ratio_dict, price_amounts = autotrader._get_ratios(coin, coin_sell_price, quote_amount)

        ## Calculation (???) & asserts
        ratio = (autotrader.db.ratios_manager.get_from_coin(coin.idx))[to_coin.idx]  # 1 element from <coin> array

        ratio_dict_to_coin = ratio_dict[(coin.idx, to_coin.idx)]  # 1 element from <coin> array
        price_amounts_to_coin = price_amounts[to_coin.symbol]     # 1 element from <coin> array

        optional_coin_buy_price, optional_coin_amount = autotrader.manager.get_market_buy_price(
                              to_coin.symbol + autotrader.config.BRIDGE.symbol,
                              quote_amount)
        assert optional_coin_buy_price == price_amounts_to_coin[0]
        assert optional_coin_amount == price_amounts_to_coin[1]

        coin_opt_coin_ratio = coin_sell_price / optional_coin_buy_price

        transaction_fee = autotrader.manager.get_fee(coin.symbol, autotrader.config.BRIDGE.symbol, True) + \
                          autotrader.manager.get_fee(to_coin.symbol, autotrader.config.BRIDGE.symbol, False)

        ## This is main ratio's elupopa :)
        assert (coin_opt_coin_ratio - transaction_fee *
                autotrader.config.SCOUT_MULTIPLIER * coin_opt_coin_ratio) - ratio == ratio_dict_to_coin

    @pytest.mark.parametrize("coin_symbol",['XLM', 'DOGE'])
    def test__jump_to_best_coin(self, DoUserConfig, mmbm, coin_symbol):
        # test on run
        db, manager, logger, config = mmbm

        coin = CoinStub.get_by_symbol(coin_symbol)
        autotrader = StubAutoTrader(manager, db, logger, config)
        from_coin_price = manager.get_ticker_price(coin_symbol + 'USDT')

        autotrader._jump_to_best_coin(coin, from_coin_price, 100, 20)
        assert True

    # TODO: Check return coin & None
    def test_bridge_scout(self, DoUserConfig, mmbm):
        # test on run
        db, manager, logger, config = mmbm

        autotrader = StubAutoTrader(manager, db, logger, config)

        pusher = []; pusher.append(autotrader.manager.balances[autotrader.config.BRIDGE.symbol])

        autotrader.manager.balances[autotrader.config.BRIDGE.symbol] = -1
        res = autotrader.bridge_scout()
        assert res is None

        autotrader.manager.balances[autotrader.config.BRIDGE.symbol] = pusher.pop()

        if 0: # Why v<0? v<0 always.

            pricer = {}

            bridge_balance = autotrader.manager.get_currency_balance(autotrader.config.BRIDGE.symbol)

            for coin in CoinStub.get_all():
                if coin.symbol not in autotrader.manager.balances.keys():
                    continue
                if (autotrader.manager.balances[coin.symbol] > 0.0) and (coin != autotrader.config.BRIDGE):
                    current_coin_price = autotrader.manager.get_ticker_price(coin.symbol + autotrader.config.BRIDGE.symbol)
                    pricer[coin.symbol] = current_coin_price
                    min_notional = autotrader.manager.get_min_notional(coin.symbol, autotrader.config.BRIDGE.symbol)
                    print('\n',coin, min_notional)
                    ratio_dict, _ = autotrader._get_ratios(coin, current_coin_price, bridge_balance)
                    print([v > 0.0 for v in ratio_dict.values()])
                    print(coin, current_coin_price, bridge_balance, ratio_dict)

            print(pricer)

    def test_update_values(self, DoUserConfig, mmbm):
        # test on run
        db, manager, logger, config = mmbm

        autotrader = StubAutoTrader(manager, db, logger, config)

        autotrader.update_values()
        assert True