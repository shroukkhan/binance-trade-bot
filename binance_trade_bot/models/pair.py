from sqlalchemy import Column, Float, ForeignKey, Integer, String, func, or_, select
from sqlalchemy.orm import column_property, relationship

from .base import Base
from .coin import Coin

class Pair(Base):
    """
    Represents a pair of coins.

    Attributes:
        id (int): The primary key of the pair.
        from_coin_id (str): The foreign key referencing the symbol of the "from" coin.
        from_coin (Coin): The relationship to the "from" coin.
        to_coin_id (str): The foreign key referencing the symbol of the "to" coin.
        to_coin (Coin): The relationship to the "to" coin.
        ratio (float): The ratio between the "from" and "to" coins.
        enabled (bool): The column property indicating if the pair is enabled.

    Methods:
        __init__(self, from_coin: Coin, to_coin: Coin, ratio=None): Initializes a Pair object.
        __repr__(self): Returns a string representation of the Pair object.
        info(self): Returns a dictionary with information about the Pair object.
    """

    __tablename__ = "pairs"

    id = Column(Integer, primary_key=True)

    from_coin_id = Column(String, ForeignKey("coins.symbol"))
    from_coin = relationship("Coin", foreign_keys=[from_coin_id], lazy="joined")

    to_coin_id = Column(String, ForeignKey("coins.symbol"))
    to_coin = relationship("Coin", foreign_keys=[to_coin_id], lazy="joined")

    ratio = Column(Float)

    enabled = column_property(
        select([func.count(Coin.symbol) == 2])
        .where(or_(Coin.symbol == from_coin_id, Coin.symbol == to_coin_id))
        .where(Coin.enabled.is_(True))
        .scalar_subquery()
    )

    def __init__(self, from_coin: Coin, to_coin: Coin, ratio=None):
        """
        Initializes a Pair object.

        Args:
            from_coin (Coin): The "from" coin.
            to_coin (Coin): The "to" coin.
            ratio (float, optional): The ratio between the "from" and "to" coins. Defaults to None.
        """
        self.from_coin = from_coin
        self.to_coin = to_coin
        self.ratio = ratio

    def __repr__(self):
        """
        Returns a string representation of the Pair object.

        Returns:
            str: A string representation of the Pair object.
        """
        return f"<{self.from_coin_id}->{self.to_coin_id} :: {self.ratio}>"

    def info(self):
        """
        Returns a dictionary with information about the Pair object.

        Returns:
            dict: A dictionary with information about the Pair object.
        """
        return {
            "from_coin": self.from_coin.info(),
            "to_coin": self.to_coin.info(),
            "ratio": self.ratio,
        }
