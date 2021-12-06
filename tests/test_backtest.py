import datetime
import os
import runpy as rr

import pytest

from binance_trade_bot.backtest import backtest
from binance_trade_bot.binance_stream_manager import BinanceOrder
from binance_trade_bot.models import Coin

from .common import dmlc, infra

# pylint:disable=fixme


@pytest.fixture(scope="function")
def DoUserConfig():
    """
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
    """

    # os.environ['CURRENT_COIN'] = 'ETH'
    os.environ["CURRENT_COIN_SYMBOL"] = "ETH"

    os.environ["API_KEY"] = "vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A"
    os.environ["API_SECRET_KEY"] = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
    # os.environ['CURRENT_COIN_SYMBOL'] = 'BTT'
    os.environ["SUPPORTED_COIN_LIST"] = "XLM TRX ICX EOS IOTA ONT QTUM ETC ADA XMR DASH NEO ATOM DOGE VET BAT OMG BTT"
    os.environ["BRIDGE_SYMBOL"] = "USDT"
    os.environ["SCOUT_MULTIPLIER"] = "5"
    os.environ["SCOUT_SLEEP_TIME"] = "1"
    os.environ["TLD"] = "com"
    os.environ["STRATEGY"] = "default"
    os.environ["BUY_TIMEOUT"] = "0"
    os.environ["SELL_TIMEOUT"] = "0"
    os.environ["BUY_ORDER_TYPE"] = "limit"
    os.environ["SELL_ORDER_TYPE"] = "market"

    yield


@pytest.mark.timeout(60)
@pytest.mark.skip(reason="Long working time")
def test_backtest_main_module_on_run(capsys, infra, DoUserConfig):
    with pytest.raises(KeyError):
        # rr.run_module('../backtest.py',run_name='__main__')
        rr.run_path("backtest.py", run_name="__main__")

    assert True


@pytest.mark.skip(reason="Long working time")
def test_backtest1_on_run(infra, DoUserConfig):
    backtest(datetime.datetime(2021, 6, 1), datetime.datetime(2021, 6, 3))
    assert True


@pytest.mark.skip(reason="Long working time")
@pytest.mark.timeout(600)
@pytest.mark.parametrize(
    "date_start",
    [
        datetime.datetime(2021, 6, 1),
    ],
)
@pytest.mark.parametrize(
    "date_end",
    [
        datetime.datetime(2021, 6, 5),
    ],
)
@pytest.mark.parametrize("interval", [10, 5, 30])
def test_backtest2_on_run(infra, DoUserConfig, date_start, date_end, interval):
    history = []
    for manager in backtest(date_start, date_end, interval=interval):
        btc_value = manager.collate_coins("BTC")
        bridge_value = manager.collate_coins(manager.config.BRIDGE.symbol)
        history.append((btc_value, bridge_value))
        btc_diff = round((btc_value - history[0][0]) / history[0][0] * 100, 3)
        bridge_diff = round((bridge_value - history[0][1]) / history[0][1] * 100, 3)

        print(datetime.datetime.now(), "-" * 40)
        print(datetime.datetime.now(), "TIME:", manager.datetime)
        print(datetime.datetime.now(), "BALANCES:", manager.balances)
        print(datetime.datetime.now(), "BTC VALUE:", btc_value, f"({btc_diff}%)")
        print(datetime.datetime.now(), f"{manager.config.BRIDGE.symbol} VALUE:", bridge_value, f"({bridge_diff}%)")

    assert True


class TestMockBinanceManager:  # pylint:disable=no-self-use
    def test_set_reinit_trader_callback(self, DoUserConfig, dmlc):
        def reinit():
            return

        _, manager, *_ = dmlc
        assert manager.reinit_trader_callback is None
        manager.set_reinit_trader_callback(reinit)
        assert manager.reinit_trader_callback is not None

    @pytest.mark.parametrize(
        "coins_list",
        [
            pytest.param([], marks=pytest.mark.xfail),
            ["XLM", "DOGE"],
            [
                "BUGAGA",
            ],
        ],
    )
    def test_set_coins(self, DoUserConfig, dmlc, coins_list):
        _, manager, *_ = dmlc

        manager.set_coins(coins_list)
        assert True

    def test_setup_websockets(self, DoUserConfig, dmlc):
        _, manager, *_ = dmlc
        manager.setup_websockets()
        assert True

    @pytest.mark.parametrize(
        "interval",
        [
            pytest.param(-10, marks=pytest.mark.xfail),
            pytest.param(0, marks=pytest.mark.xfail),
            10,
            20,
            1440 - 1,
            1440,
            1440 + 1,
            100 * 1440,
        ],
    )
    def test_increment(self, DoUserConfig, dmlc, interval):
        _, manager, *_ = dmlc
        old_datetime = manager.datetime
        manager.increment(interval=interval)

        assert manager.datetime == datetime.timedelta(minutes=interval) + old_datetime

    def test_get_fee(self, DoUserConfig, dmlc):
        _, manager, *_ = dmlc
        assert manager.get_fee("GOT", "BAI", False) == 0.001
        assert manager.get_fee("GOT", "BAI", True) == 0.001

    # TODO: Not verify across historical_klines request?
    def test_get_ticker_price(self, DoUserConfig, dmlc):
        _, manager, *_ = dmlc
        val = manager.get_ticker_price("XLMUSDT")

        assert val

    def test_get_currency_balance(self, DoUserConfig, dmlc):
        _, manager, *_ = dmlc
        assert manager.get_currency_balance("GOT") == 0.0
        assert manager.get_currency_balance("XLM") == 100.0
        assert manager.get_currency_balance("DOGE") == 101.0
        assert manager.get_currency_balance("BTT") == 102.0
        assert manager.get_currency_balance("BAD") == 103.0
        assert manager.get_currency_balance("USDT") == 1000.0

    def test_get_market_sell_price(self, DoUserConfig, dmlc):
        _, manager, *_ = dmlc
        val = manager.get_ticker_price("XLMUSDT")
        price01 = manager.get_market_sell_price("XLMUSDT", 20)
        assert price01[0]
        assert price01[1] == val * 20.0

    @pytest.mark.parametrize("ticker", ["XLMUSDT", "BTTUSDT", "BTCUSDT"])
    def test_get_market_buy_price(self, DoUserConfig, dmlc, ticker):
        _, manager, *_ = dmlc
        qoute = 100.0
        price = manager.get_ticker_price(ticker)
        price01 = manager.get_market_buy_price(ticker, qoute)
        assert price01[0]
        assert price01[1] == qoute / price

    # TODO: === previous? Are is sell or buy
    @pytest.mark.skip(reason="Unclear, buy or sell?")
    def test_get_market_sell_price_fill_quote(self, DoUserConfig, dmlc):
        _, manager, *_ = dmlc
        qoute = 100.0
        price = manager.get_ticker_price("XLMUSDT")
        price01 = manager.get_market_sell_price_fill_quote("XLMUSDT", qoute)
        assert price01[0]
        assert price01[1] == qoute / price

    @pytest.mark.parametrize("origin_coin", ["BTT", "XLM"])
    @pytest.mark.parametrize(
        "target_coin",
        [
            "USDT",
        ],
    )
    def test_buy_alt(self, DoUserConfig, dmlc, origin_coin, target_coin):
        _, manager, *_ = dmlc

        from_coin_price = manager.get_ticker_price(origin_coin + target_coin)

        buy_price = from_coin_price + 1e-14
        with pytest.raises(AssertionError):
            res: BinanceOrder = manager.buy_alt(origin_coin, target_coin, buy_price)

        target_balance = manager.get_currency_balance(target_coin)
        order_quantity = manager.buy_quantity(origin_coin, target_coin, target_balance, from_coin_price)
        target_quantity = order_quantity * from_coin_price

        buy_price = from_coin_price
        res: BinanceOrder = manager.buy_alt(origin_coin, target_coin, buy_price)

        assert res.cumulative_quote_qty == target_quantity
        assert res.price == from_coin_price
        assert res.cumulative_filled_quantity == order_quantity

        target_balance = manager.get_currency_balance(target_coin)
        order_quantity = manager.buy_quantity(origin_coin, target_coin, target_balance, from_coin_price)
        target_quantity = order_quantity * from_coin_price

        buy_price = 0.0
        res: BinanceOrder = manager.buy_alt(origin_coin, target_coin, buy_price)

        assert res.cumulative_quote_qty == target_quantity
        assert res.price == from_coin_price
        assert res.cumulative_filled_quantity == order_quantity

    @pytest.mark.parametrize("origin_coin", ["BTT", "XLM"])
    @pytest.mark.parametrize(
        "target_coin",
        [
            "USDT",
        ],
    )
    def test_sell_alt(self, DoUserConfig, dmlc, origin_coin, target_coin):
        _, manager, *_ = dmlc

        from_coin_price = manager.get_ticker_price(origin_coin + target_coin)

        sell_price = from_coin_price + 1e-14
        with pytest.raises(AssertionError):
            manager.sell_alt(origin_coin, target_coin, sell_price)

        sell_price = from_coin_price
        origin_balance = manager.get_currency_balance(origin_coin)
        order_quantity = manager.sell_quantity(origin_coin, target_coin, origin_balance)
        target_quantity = order_quantity * from_coin_price

        res = manager.sell_alt(origin_coin, target_coin, sell_price)

        assert res.cumulative_quote_qty == target_quantity
        assert res.price == from_coin_price
        assert res.cumulative_filled_quantity == order_quantity

    def test_collate_coins(self, DoUserConfig, dmlc):
        _, manager, *_ = dmlc

        manager.balances = dict()
        manager.balances["XMR"] = 300

        manager.get_ticker_price("XMRUSDT")

        res = manager.collate_coins("XMR")

        assert res == 300

        manager.balances = dict()
        manager.balances["XMR"] = 400
        manager.balances["BTT"] = 500

        price1 = manager.get_ticker_price("XMRUSDT")
        price2 = manager.get_ticker_price("BTTUSDT")

        res = manager.collate_coins("USDT")

        assert res == 400 * price1 + 500 * price2

    def test_collate_coins1(self, DoUserConfig, dmlc):  # , target_ticker):
        _, manager, *_ = dmlc

        manager.config.BRIDGE = Coin("BTT")
        manager.balances = dict()
        manager.balances[manager.config.BRIDGE.symbol] = 400

        res = manager.collate_coins(manager.config.BRIDGE.symbol)
        # print(f'\nres - {res}')
        assert res == 400.0
