import pytest

import os, datetime

from sqlalchemy.orm import Session

from binance_trade_bot.database import Database, TradeLog
from binance_trade_bot.logger import Logger
from binance_trade_bot.config import Config
from binance_trade_bot.models.coin import Coin
from binance_trade_bot.models.pair import Pair
from binance_trade_bot.models.coin_value import CoinValue

from .common import infra


@pytest.fixture(scope='class', autouse=True)
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


class TestDatabase:

    @pytest.mark.xfail
    def test_socketio_connect(self):
        # test on run
        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()

        result: bool = dbtest.socketio_connect()
        assert result

    def test_db_session(self):
        # test on run
        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()

        session: Session = dbtest.db_session()
        assert session

    @pytest.mark.skip(reason='Not actual')
    def test_schedule_execute_later(self):
        assert False

    @pytest.mark.skip(reason='Not actual')
    def test_execute_postponed_calls(self):
        assert False

    def test_manage_session(self):
        # test on run
        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()

        session: Session = dbtest.manage_session(session=None)
        assert session
        session: Session = dbtest.manage_session(session=session)
        assert session
        session: Session = dbtest.manage_session()
        assert session

    def test_set_coins(self):
        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()

        # testing empty
        dbtest.set_coins([])
        listCoins = dbtest.get_coins(only_enabled=True)
        for ii in listCoins:
            assert (ii.symbol in config.SUPPORTED_COIN_LIST) or (ii.symbol == 'BAD'), "No matched "+ii.symbol
        assert len(listCoins) == 0, "Not matched size"

        # testing not empty
        dbtest.set_coins(config.SUPPORTED_COIN_LIST)
        listCoins = dbtest.get_coins(only_enabled=True)
        for ii in listCoins:
            assert (ii.symbol in config.SUPPORTED_COIN_LIST) or ('BAD' == ii.symbol), "No matched "+ii.symbol
        assert len(listCoins) == len(config.SUPPORTED_COIN_LIST), "Not matched size"

    @pytest.mark.parametrize('coins,counts', [([], 0), (['BAD'], 0), (['DOGE'], 0), (['ATR', 'XRL'], 0)])
    def test_get_coins_False(self, coins, counts):

        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()

        fullres = dbtest.get_coins(False); fullres = [ii.symbol for ii in fullres]
        dbtest.set_coins(coins)

        listCoins = dbtest.get_coins(only_enabled=False)

        for ii in listCoins:
            assert ii.symbol in fullres, "Not found: "+ii.symbol
        assert len(listCoins) == len(fullres), f"Not matched size"

    @pytest.mark.parametrize('coins,counts', [([], 0), (['BAD'], 1), (['DOGE'], 1), (['ATR', 'XRL'], 2)])
    def test_get_coins_True(self, coins, counts):

        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()

        fullres = dbtest.get_coins(False); fullres = [ii.symbol for ii in fullres]
        dbtest.set_coins(coins)

        listCoins = dbtest.get_coins(only_enabled=True)

        for ii in listCoins:
            assert ii.symbol in coins, "Not found: "+ii.symbol
        assert len(listCoins) == counts, f"Not matched size"

    def test_get_coin(self):

        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()

        dbtest.set_coins(config.SUPPORTED_COIN_LIST)

        # testing string
        ccoin = dbtest.get_coin(config.SUPPORTED_COIN_LIST[0])
        assert config.SUPPORTED_COIN_LIST[0] == ccoin.symbol

        # testing type
        ccoin = dbtest.get_coin(Coin(config.SUPPORTED_COIN_LIST[-1]))
        assert config.SUPPORTED_COIN_LIST[-1] == ccoin.symbol

    def test_set_current_coin(self):

        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()

        dbtest.set_coins(config.SUPPORTED_COIN_LIST)

        # testing string
        dbtest.set_current_coin(config.SUPPORTED_COIN_LIST[0])
        ccoin: Coin = dbtest.get_current_coin()
        assert config.SUPPORTED_COIN_LIST[0] == ccoin.symbol

        # testing type
        dbtest.set_current_coin(Coin(config.SUPPORTED_COIN_LIST[-1]))
        ccoin: Coin = dbtest.get_current_coin()
        assert config.SUPPORTED_COIN_LIST[-1] == ccoin.symbol

    def test_get_current_coin(self):
        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()

        dbtest.set_coins(config.SUPPORTED_COIN_LIST)

        # testing string
        dbtest.set_current_coin(config.SUPPORTED_COIN_LIST[0])
        ccoin: Coin = dbtest.get_current_coin()
        assert config.SUPPORTED_COIN_LIST[0] == ccoin.symbol

        # testing type
        dbtest.set_current_coin(Coin(config.SUPPORTED_COIN_LIST[-1]))
        ccoin: Coin = dbtest.get_current_coin()
        assert config.SUPPORTED_COIN_LIST[-1] == ccoin.symbol

    @pytest.mark.parametrize('from_coin', [Coin('XMR'), 'XMR'])
    @pytest.mark.parametrize('to_coin', [Coin('DOGE'), 'EOS'])
    def test_get_pair(self, from_coin, to_coin):

        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest: Database = Database(logger, config)
        dbtest.create_database()
        dbtest.set_coins(config.SUPPORTED_COIN_LIST)

        pair = dbtest.get_pair(from_coin, to_coin)
        assert isinstance(pair,Pair)

    @pytest.mark.skip
    def test_batch_log_scout(self):
        assert False

    def test_prune_scout_history(self):

        # Test on run
        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()
        dbtest.set_coins(config.SUPPORTED_COIN_LIST)
        dbtest.prune_scout_history()
        assert True

    def test_prune_value_history(self):

        # Test on run
        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()
        dbtest.set_coins(config.SUPPORTED_COIN_LIST)
        dbtest.prune_value_history()
        assert True

    def test_create_database(self):
        # Test on run
        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()
        assert True

    @pytest.mark.parametrize('from_coin', ['XML', 'ATR'])
    @pytest.mark.parametrize('to_coin', ['BTT', 'XML'])
    @pytest.mark.parametrize('selling', [True, False])
    def test_start_trade_log(self, from_coin: str, to_coin: str, selling: bool):

        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()

        tradeLog = dbtest.start_trade_log(from_coin, to_coin, selling)
        # print(type(tradeLog))
        # print(tradeLog)

        assert True

    # TODO: parameter coin in send_update not using?
    @pytest.mark.parametrize('coin', [None, 'XML', Coin('ATR'), 'BAD'])
    def test_send_update(self, coin):
        # test on run
        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()
        dbtest.send_update(coin)
        assert True

    @pytest.mark.skip(reason="Not actual")
    def test_migrate_old_state(self):
        assert False

    def test_commit_ratios(self):
        # test on run
        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()
        dbtest.set_coins(config.SUPPORTED_COIN_LIST)

        dbtest.commit_ratios()
        assert True

    def test_batch_update_coin_values(self):
        # test on run
        logger = Logger("db_testing", enable_notifications=False)
        config = Config()

        dbtest = Database(logger, config)
        dbtest.create_database()

        dbtest.batch_update_coin_values([])

        vlist = [CoinValue(Coin('BTT'), 4.0, 5000.0, 0.89, 'HOURLY', None),
                 CoinValue(Coin('BTT'), 4.0, 5000.0, 0.89, 'DAILY', datetime.datetime.now()), ]
        dbtest.batch_update_coin_values(vlist)

        assert True


class TestTradeLog:
    def test_set_ordered(self):
        # test on run
        config = Config()

        dbtest: Database = Database(Logger("db_testing", enable_notifications=False), config)
        dbtest.create_database()
        dbtest.set_coins(config.SUPPORTED_COIN_LIST)

        trade  = TradeLog(dbtest, 'XMR', 'DOGE', False)
        trade.set_ordered(110.0, 30.0, 60)
        trade.set_complete(20.0)

        assert True

    def test_set_complete(self):
        # test on run
        config = Config()

        dbtest = Database(Logger("db_testing", enable_notifications=False), config)
        dbtest.create_database()
        dbtest.set_coins(config.SUPPORTED_COIN_LIST)

        trade  = TradeLog(dbtest, 'XMR', 'DOGE', True)
        trade.set_ordered(110.0, 30.0, 60)
        trade.set_complete(20.0)

        assert True
