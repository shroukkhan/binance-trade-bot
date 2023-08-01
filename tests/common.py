import datetime
import pathlib
import shutil
from typing import Dict, List

import pytest
from binance import Client
from sqlitedict import SqliteDict

from binance_trade_bot.backtest import MockBinanceManager, MockDatabase
from binance_trade_bot.binance_stream_manager import BinanceCache
from binance_trade_bot.config import Config
from binance_trade_bot.logger import Logger


def rm_rf(paths: List[pathlib.Path]):
    """
    Recursively remove directories and their contents.

    Args:
        paths (List[pathlib.Path]): List of directory paths to be removed.

    Returns:
        None
    """
    for path in paths:
        if path.exists():
            shutil.rmtree(path)


@pytest.fixture(autouse=True)
def infra(delete_ok=False, delete_ok_first=False, dirs=None):
    """
    Fixture for initializing infrastructure resources.

    Args:
        delete_ok (bool, optional): Flag indicating whether to delete the directories after the test. Defaults to False.
        delete_ok_first (bool, optional): Flag indicating whether to delete the directories before the test. Defaults to False.
        dirs (list, optional): List of directory paths to be created. Defaults to ["logs", "data"].

    Yields:
        None

    Returns:
        None
    """
    dirs = [pathlib.Path(directory) for directory in dirs or ["logs", "data"]]

    if delete_ok_first:
        rm_rf(dirs)

    for path in dirs:
        path.mkdir(exist_ok=True)

    yield

    if delete_ok:
        rm_rf(dirs)


@pytest.fixture()
def dmlc():
    """
    Fixture for setting up a test environment with mock objects.

    Returns:
        Tuple: A tuple containing the following objects:
            - db (MockDatabase): A mock database object.
            - manager (MockBinanceManager): A mock Binance manager object.
            - logger (Logger): A logger object.
            - config (Config): A configuration object.
    """
    logger: Logger = Logger(logging_service="guliguli")
    config: Config = Config()
    sqlite_cache = SqliteDict("data/testtest_cache.db")

    db = MockDatabase(logger, config)
    db.create_database()
    db.set_coins(config.SUPPORTED_COIN_LIST)

    start_date: datetime = datetime.datetime(2021, 6, 1)
    start_balances: Dict[str, float] = dict()
    start_balances["XLM"] = 100
    start_balances["DOGE"] = 101
    start_balances["BTT"] = 102
    start_balances["BAD"] = 103
    start_balances["USDT"] = 1000

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

    # manager.close()
    # db.close()
    sqlite_cache.close()


def test_common(infra):
    return
