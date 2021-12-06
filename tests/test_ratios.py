import random
from typing import List

import pytest

from binance_trade_bot.models import Coin, Pair
from binance_trade_bot.ratios import CoinStub, RatiosManager


@pytest.fixture
def coins_stubs() -> List[CoinStub]:
    CoinStub.reset()
    symbols = ["XMR", "EOS", "DOGE", "BTC"]
    return [CoinStub.create(symbol) for symbol in symbols]


@pytest.fixture
def ratios(coins_stubs: List[CoinStub]) -> List[Pair]:
    coins = [Coin(stub.symbol, True) for stub in coins_stubs]
    return [
        Pair(coin_from, coin_to, random.random())
        for coin_from in coins
        for coin_to in coins
        if coin_from is not coin_to
    ]


class TestCoinStubs:
    @staticmethod
    def test_coin_stubs_memoization_by_idx(coins_stubs: List[CoinStub]):
        for coin_stub in coins_stubs:
            assert coin_stub is CoinStub.get_by_idx(coin_stub.idx)

    @staticmethod
    def test_coin_stubs_memoization_by_symbol(coins_stubs: List[CoinStub]):
        for coin_stub in coins_stubs:
            assert coin_stub is CoinStub.get_by_symbol(coin_stub.symbol)

    @staticmethod
    def test_get_all(coins_stubs: List[CoinStub]):
        all_stubs = CoinStub.get_all()
        assert all_stubs == coins_stubs

    @staticmethod
    def test_repr(coins_stubs: List[CoinStub]):
        for coin in coins_stubs:
            assert repr(coin) == f"CoinStub({coin.idx}, {coin.symbol})"


class TestRatioManager:
    @staticmethod
    def test_manager_creation(coins_stubs: List[CoinStub]):
        manager = RatiosManager()
        assert manager.n == len(coins_stubs)

    @staticmethod
    def test_manager_creation_with_ratios(ratios: List[Pair]):
        manager = RatiosManager(ratios)
        assert manager.n == CoinStub.len_coins()

    @staticmethod
    def test_dirty(ratios: List[Pair]):
        manager = RatiosManager(ratios)
        value_to_write = 42.0
        cells_to_modify = {(0, 1), (2, 3), (3, 0)}
        for cell in cells_to_modify:
            manager.set(cell[0], cell[1], value_to_write)
        for cell in manager.get_dirty():
            assert cell in cells_to_modify
            assert manager.get(cell[0], cell[1]) == value_to_write

    @staticmethod
    def test_rollback(ratios: List[Pair]):
        manager = RatiosManager(ratios)
        cell_1_old_value = manager.get(0, 2)
        cell_2_old_value = manager.get(3, 1)
        manager.set(0, 2, 34.0)
        manager.set(0, 2, 42.0)
        manager.set(3, 1, 55.0)
        assert manager.get(0, 2) == 42.0
        manager.rollback()
        assert len(manager.get_dirty()) == 0
        assert manager.get(0, 2) == cell_1_old_value
        assert manager.get(3, 1) == cell_2_old_value

    @staticmethod
    def test_commit(ratios: List[Pair]):
        manager = RatiosManager(ratios)
        manager.set(0, 2, 34.0)
        manager.set(0, 2, 42.0)
        manager.set(3, 1, 55.0)
        manager.commit()
        assert len(manager.get_dirty()) == 0
        assert manager.get(0, 2) == 42.0
        assert manager.get(3, 1) == 55.0

    @staticmethod
    def test_row_col_retrieve(coins_stubs: List[CoinStub]):
        manager = RatiosManager()
        counter = 0
        for i in range(len(coins_stubs)):
            for j in range(len(coins_stubs)):
                manager.set(i, j, counter)
                counter += 1
        manager.commit()
        n = len(coins_stubs)
        row_0 = manager.get_from_coin(0)
        assert len(row_0) == n
        assert list(row_0) == list(map(float, range(n)))
        col_0 = manager.get_to_coin(0)
        assert len(col_0) == n
        assert list(col_0) == [float(i * n) for i in range(n)]
        row_last = manager.get_from_coin(n - 1)
        assert len(row_last) == n
        assert list(row_last) == [float(n * (n - 1) + i) for i in range(n)]
        col_last = manager.get_to_coin(n - 1)
        assert len(col_last) == n
        assert list(col_last) == [float(n * i + (n - 1)) for i in range(n)]
