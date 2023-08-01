from array import array
from math import nan
from typing import Dict, Iterable, KeysView, List, Optional, Tuple, Type

from binance_trade_bot.models import Pair


class CoinStub:
    """
    Represents a coin stub.

    Attributes:
        _instances (List[CoinStub]): A list of all CoinStub instances.
        _instances_by_symbol (Dict[str, CoinStub]): A dictionary mapping symbols to CoinStub instances.
        idx (int): The index of the CoinStub instance.
        symbol (str): The symbol of the coin.

    Methods:
        __init__(self, ratio_idx: int, symbol: str): Initializes a CoinStub instance.
        __repr__(self): Returns a string representation of the CoinStub instance.
        create(cls: Type[CoinStub], symbol: str) -> CoinStub: Creates a new CoinStub instance.
        get_by_idx(cls: Type[CoinStub], idx: int) -> CoinStub: Retrieves a CoinStub instance by index.
        get_by_symbol(cls: Type[CoinStub], symbol: str) -> CoinStub: Retrieves a CoinStub instance by symbol.
        reset(cls: Type[CoinStub]): Resets the CoinStub class by clearing all instances.
        len_coins(cls: Type[CoinStub]) -> int: Returns the number of CoinStub instances.
        get_all(cls: Type[CoinStub]) -> List[CoinStub]: Returns a list of all CoinStub instances.
    """

    _instances: List["CoinStub"] = []
    _instances_by_symbol: Dict[str, "CoinStub"] = {}

    def __init__(self, ratio_idx: int, symbol: str):
        """
        Don't call this directly, use create method
        :param ratio_idx:
        :param symbol:
        """
        self.idx = ratio_idx
        self.symbol = symbol

    def __repr__(self):
        return f"CoinStub({self.idx}, {self.symbol})"

    @classmethod
    def create(cls: Type["CoinStub"], symbol: str) -> "CoinStub":
        """
        Creates a new CoinStub instance.

        Args:
            cls (Type[CoinStub]): The CoinStub class.
            symbol (str): The symbol of the coin.

        Returns:
            CoinStub: The newly created CoinStub instance.
        """
        idx = len(cls._instances)
        new_instance = cls(idx, symbol)
        cls._instances.append(new_instance)
        cls._instances_by_symbol[symbol] = new_instance
        return new_instance

    @classmethod
    def get_by_idx(cls: Type["CoinStub"], idx: int) -> "CoinStub":
        """
        Retrieves a CoinStub instance by index.

        Args:
            cls (Type[CoinStub]): The CoinStub class.
            idx (int): The index of the CoinStub instance.

        Returns:
            CoinStub: The CoinStub instance with the specified index.
        """
        return cls._instances[idx]

    @classmethod
    def get_by_symbol(cls: Type["CoinStub"], symbol: str) -> "CoinStub":
        """
        Retrieves a CoinStub instance by symbol.

        Args:
            cls (Type[CoinStub]): The CoinStub class.
            symbol (str): The symbol of the coin.

        Returns:
            CoinStub: The CoinStub instance with the specified symbol, or None if not found.
        """
        return cls._instances_by_symbol.get(symbol, None)

    @classmethod
    def reset(cls: Type["CoinStub"]):
        """
        Resets the CoinStub class by clearing all instances.

        Args:
            cls (Type[CoinStub]): The CoinStub class.
        """
        cls._instances.clear()
        cls._instances_by_symbol.clear()

    @classmethod
    def len_coins(cls: Type["CoinStub"]) -> int:
        """
        Returns the number of CoinStub instances.

        Args:
            cls (Type[CoinStub]): The CoinStub class.

        Returns:
            int: The number of CoinStub instances.
        """
        return len(cls._instances)

    @classmethod
    def get_all(cls: Type["CoinStub"]) -> List["CoinStub"]:
        """
        Returns a list of all CoinStub instances.

        Args:
            cls (Type[CoinStub]): The CoinStub class.

        Returns:
            List[CoinStub]: A list of all CoinStub instances.
        """
        return cls._instances


class RatiosManager:
    """
    Provides memory storage for all ratios in a form of dense square matrix with a row major order.
    It also has a basic transaction support in a form of commit/rollback calls, which should be much
    more lightweight than SQLAlchemy ORM does.
    
    A dense square matrix with a row major order refers to a matrix where the elements are stored in memory in a contiguous manner, row by row. In other words, the elements of each row are stored together in memory, and the rows are arranged consecutively.
    """

    def __init__(self, ratios: Optional[Iterable[Pair]] = None):
        self.n = CoinStub.len_coins()
        self._data = array("d", (nan if i != j else 1.0 for i in range(self.n) for j in range(self.n)))
        self._dirty: Dict[Tuple[int, int], float] = {}
        self._ids: Optional[array] = None
        if ratios is not None:
            self._ids = array("Q", (0 for _ in range(self.n * self.n)))
            for pair in ratios:
                i = CoinStub.get_by_symbol(pair.from_coin.symbol).idx
                j = CoinStub.get_by_symbol(pair.to_coin.symbol).idx
                val = pair.ratio if pair.ratio is not None else nan
                pair_id = pair.id if pair.id is not None else 0
                idx = self.n * i + j
                self._data[idx] = val
                self._ids[idx] = pair_id

    def set(self, from_coin_idx: int, to_coin_idx: int, val: float):
        cell = (from_coin_idx, to_coin_idx)
        if cell not in self._dirty:
            self._dirty[cell] = self._data[self.n * cell[0] + cell[1]]
        self._data[self.n * cell[0] + cell[1]] = val

    def get(self, from_coin_idx: int, to_coin_idx: int) -> float:
        return self._data[self.n * from_coin_idx + to_coin_idx]

    def get_from_coin(self, from_coin_idx: int):
        return self._data[self.n * from_coin_idx: self.n * (from_coin_idx + 1)]

    def get_to_coin(self, to_coin_idx: int):
        return self._data[to_coin_idx:: self.n]

    def get_dirty(self) -> KeysView[Tuple[int, int]]:
        return self._dirty.keys()

    def get_pair_id(self, from_coin_idx: int, to_coin_idx: int) -> int:
        return self._ids[from_coin_idx * self.n + to_coin_idx]

    def rollback(self):
        for cell, old_value in self._dirty.items():
            self._data[self.n * cell[0] + cell[1]] = old_value
        self._dirty.clear()

    def commit(self):
        self._dirty.clear()
