import configparser
import os

from .models import Coin

CFG_FL_NAME = "user.cfg"
USER_CFG_SECTION = "binance_user_config"


class Config:  # pylint: disable=too-few-public-methods,too-many-instance-attributes
    def __init__(self):
        # Init config
        config = configparser.ConfigParser()
        config["DEFAULT"] = {
            "bridge": "USDT",
            "use_margin": "true",
            "scout_multiplier": "5",
            "scout_margin": "0.8",
            "scout_sleep_time": "1",
            "hourToKeepScoutHistory": "1",
            "tld": "com",
            "strategy": "default",
            "enable_paper_trading": False,
            "api_port": 5123,
            "use_wiggle": True,
            "wiggle_factor": 0.0005,
            "coins_to_gain": "ETH,BTC,XRP,SOL,ADA",
            "coins_to_gain_pct": 0.5  # only sell  0.5 ( or 50% ) of long hold coins
        }

        if not os.path.exists(CFG_FL_NAME):
            print("No configuration file (user.cfg) found! See README. Assuming default config...")
            config[USER_CFG_SECTION] = {}
        else:
            config.read(CFG_FL_NAME)

        self.BRIDGE_SYMBOL = os.environ.get("BRIDGE_SYMBOL") or config.get(USER_CFG_SECTION, "bridge")
        self.BRIDGE = Coin(self.BRIDGE_SYMBOL, False)

        # Prune settings
        self.SCOUT_HISTORY_PRUNE_TIME = float(
            os.environ.get("HOURS_TO_KEEP_SCOUTING_HISTORY") or config.get(USER_CFG_SECTION, "hourToKeepScoutHistory")
        )

        # Get config for scout
        self.SCOUT_MULTIPLIER = float(
            os.environ.get("SCOUT_MULTIPLIER") or config.get(USER_CFG_SECTION, "scout_multiplier")
        )
        self.SCOUT_SLEEP_TIME = int(
            os.environ.get("SCOUT_SLEEP_TIME") or config.get(USER_CFG_SECTION, "scout_sleep_time")
        )

        use_margin = os.environ.get("USE_MARGIN") or config.get(USER_CFG_SECTION, "use_margin")
        self.USE_MARGIN = {"true": True, "false": False}.get(str(use_margin).lower())
        if self.USE_MARGIN is None:
            raise ValueError("use_margin parameter must be either 'true' or 'false'")
        self.SCOUT_MARGIN = os.environ.get("SCOUT_MARGIN") or config.get(USER_CFG_SECTION, "scout_margin")
        self.SCOUT_MARGIN = float(self.SCOUT_MARGIN)

        # Get config for binance
        self.BINANCE_API_KEY = os.environ.get("API_KEY") or config.get(USER_CFG_SECTION, "api_key")
        self.BINANCE_API_SECRET_KEY = os.environ.get("API_SECRET_KEY") or config.get(USER_CFG_SECTION, "api_secret_key")
        self.BINANCE_TLD = os.environ.get("TLD") or config.get(USER_CFG_SECTION, "tld")

        # Get supported coin list from the environment
        supported_coin_list = [
            coin.strip() for coin in os.environ.get("SUPPORTED_COIN_LIST", "").split() if coin.strip()
        ]
        # Get supported coin list from supported_coin_list file
        if not supported_coin_list and os.path.exists("supported_coin_list"):
            with open("supported_coin_list") as rfh:
                for line in rfh:
                    line = line.strip()
                    if not line or line.startswith("#") or line in supported_coin_list:
                        continue
                    supported_coin_list.append(line)
        self.SUPPORTED_COIN_LIST = supported_coin_list

        self.CURRENT_COIN_SYMBOL = os.environ.get("CURRENT_COIN_SYMBOL") or config.get(USER_CFG_SECTION, "current_coin")

        self.STRATEGY = os.environ.get("STRATEGY") or config.get(USER_CFG_SECTION, "strategy")
        enable_paper_trading = (
                os.environ.get("ENABLE_PAPER_TRADING") or config.get(USER_CFG_SECTION,
                                                                     "enable_paper_trading")
        )
        self.ENABLE_PAPER_TRADING = str(enable_paper_trading).lower() == "true"

        # extra config added by khan
        self.WIGGLE_FACTOR = float(
            os.environ.get("WIGGLE_FACTOR") or config.get(USER_CFG_SECTION, "wiggle_factor")
        )

        use_wiggle = os.environ.get("USE_WIGGLE") or config.get(USER_CFG_SECTION, "use_wiggle")
        self.USE_WIGGLE = {"true": True, "false": False}.get(str(use_wiggle).lower())

        coins_to_gain = [
            coin.strip() for coin in config.get(USER_CFG_SECTION, "coins_to_gain").split(',') if coin.strip()
        ]
        self.COINS_TO_GAIN = coins_to_gain  # we do not jump OUT of these coins..because these coins are for long term holding

        self.COINS_TO_GAIN_PCT = float(
            os.environ.get("COINS_TO_GAIN_PCT") or config.get(USER_CFG_SECTION, "coins_to_gain_pct")
        )

        # api port
        self.API_PORT = int(
            os.environ.get("API_PORT") or config.get(USER_CFG_SECTION, "API_PORT")
        )
