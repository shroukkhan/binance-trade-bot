import random
import sys
from datetime import datetime

from binance_trade_bot.auto_trader import AutoTrader
from binance_trade_bot.ratios import CoinStub


class Strategy(AutoTrader):
    def initialize(self):
        super().initialize()
        self.initialize_current_coin()

        gain = "We shall gain coins in the following manner:\n"
        for key in self.config.COINS_TO_GAIN:
            gain += f"{key} -> {self.config.COINS_TO_GAIN[key] * 100}%\n"

        self.logger.info(gain)


    def scout(self):
        """
        Scout for potential jumps from the current coin to another coin
        """
        current_coin = self.db.get_current_coin()
        current_coin_amount = self.manager.get_currency_balance(current_coin.symbol)
        # Display on the console, the current coin+Bridge, so users can see *some* activity and not think the bot has
        # stopped. Not logging though to reduce log size.
        print(
            f"{datetime.now()} - CONSOLE - INFO - I am scouting the best trades. "
            f"Current coin: {current_coin + self.config.BRIDGE} ",
            end="\r",
        )

        current_coin_price, current_coin_quote = self.manager.get_market_sell_price(
            current_coin + self.config.BRIDGE, current_coin_amount
        )

        if current_coin_price is None:
            self.logger.info("Skipping scouting... current coin {} not found".format(current_coin + self.config.BRIDGE))
            return
        if current_coin_amount * current_coin_price < self.manager.get_min_notional(
                current_coin.symbol, self.config.BRIDGE.symbol
        ):
            self.logger.info(f"Current coin {current_coin.symbol} amount is below min notional, skip scouting")
            return

        self._jump_to_best_coin(
            CoinStub.get_by_symbol(current_coin.symbol), current_coin_price, current_coin_quote, current_coin_amount
        )

    def bridge_scout(self):
        current_coin = self.db.get_current_coin()
        if self.manager.get_currency_balance(current_coin.symbol) > self.manager.get_min_notional(
                current_coin.symbol, self.config.BRIDGE.symbol
        ):
            # Only scout if we don't have enough of the current coin
            return
        new_coin = super().bridge_scout()
        if new_coin is not None:
            self.db.set_current_coin(new_coin)

    def initialize_current_coin(self):
        """
        Decide what is the current coin, and set it up in the DB.
        """
        if self.db.get_current_coin() is None:
            current_coin_symbol = self.config.CURRENT_COIN_SYMBOL
            if not current_coin_symbol:
                current_coin_symbol = random.choice(self.config.SUPPORTED_COIN_LIST)
                self.logger.info(f"Picked a <RANDOM> initial coin: {current_coin_symbol}")

            self.logger.info(f"[initialize_current_coin] Setting initial coin to {current_coin_symbol}")

            if current_coin_symbol not in self.config.SUPPORTED_COIN_LIST:
                sys.exit("***\nERROR!\nSince there is no backup file, a proper coin name must be provided at init\n***")
            self.db.set_current_coin(current_coin_symbol)

        current_coin = self.db.get_current_coin()
        current_amount = self.manager.get_currency_balance(current_coin.symbol)
        # if we don't have a configuration, we selected a coin at random... Buy it so we can start trading.
        if current_amount == 0.0:  # current coin symbol is empty, also current amount is 0.0
            self.logger.info(f"[initialize_current_coin] Purchasing {current_coin} to begin trading")
            self.manager.buy_alt(
                current_coin.symbol,
                self.config.BRIDGE.symbol,
                self.manager.get_ticker_price(current_coin.symbol + self.config.BRIDGE.symbol),
            )
            self.logger.info("[initialize_current_coin] Ready to start trading")
            # self.transaction_through_bridge(
            #     from_coin=current_coin_symbol,
            #     to_coin='ADA',
            #     sell_price=88.33,
            #     buy_price=0.8597)
        else:
            self.logger.info(f"[initialize_current_coin] We have {current_amount} of {current_coin.symbol}, we are ready to start trading")

