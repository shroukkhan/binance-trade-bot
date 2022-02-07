from datetime import datetime

from binance_trade_bot import backtest

if __name__ == "__main__":
    history = []
    for manager in backtest(start_date=datetime(year=2021,
                                                month=12,
                                                day=29,
                                                hour=6,
                                                minute=51),
                            end_date=datetime.now(),
                            start_balances={'USDT': 150},
                            starting_coin='SOL',
                            ):
        btc_value = manager.collate_coins("BTC")
        bridge_value = manager.collate_coins(manager.config.BRIDGE.symbol)
        history.append((btc_value, bridge_value))
        btc_diff = round((btc_value - history[0][0]) / history[0][0] * 100, 3)
        bridge_diff = round((bridge_value - history[0][1]) / history[0][1] * 100, 3)
        print("------")
        print("TIME:", manager.datetime)
        print("BALANCES:", manager.balances)
        print("BTC VALUE:", btc_value, f"({btc_diff}%)")
        print(f"{manager.config.BRIDGE.symbol} VALUE:", bridge_value, f"({bridge_diff}%)")
        print("------")
