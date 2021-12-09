"""
This script will display a table of the latest values in ratio_dict,
i.e. the current ratio changes.
"""

import os
import sqlite3
from configparser import ConfigParser
from datetime import datetime

from tabulate import tabulate

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

db_file_path = "data/crypto_trading.db"
assert os.path.exists(db_file_path), f"⚠ Unable to find database file at '{db_file_path}'"

user_cfg_file_path = "user.cfg"
assert os.path.exists(user_cfg_file_path), f"⚠ Unable to find user config file at '{user_cfg_file_path}'"
with open(user_cfg_file_path) as cfg:
    config = ConfigParser()
    config.read_file(cfg)
    use_margin = config.get("binance_user_config", "use_margin")

con = sqlite3.connect(db_file_path)
con.row_factory = sqlite3.Row
cur = con.cursor()
cur.execute(
    """
    SELECT pairs.from_coin_id, pairs.to_coin_id, scout_history.ratio_diff FROM scout_history
    LEFT JOIN pairs ON scout_history.pair_id = pairs.id WHERE datetime = (SELECT max(datetime) from scout_history)
    ORDER BY scout_history.ratio_diff ASC;
"""
)

ratio_dict = cur.fetchall()

last_time = cur.execute("SELECT max(datetime) as datetime FROM scout_history LIMIT 1;").fetchone()
last_time = datetime.strptime(last_time["datetime"], "%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d %H:%M:%S")

current_coin = ratio_dict[0]["from_coin_id"]

ratio_dict_out = []
for x in ratio_dict:
    l = [x["to_coin_id"], x["ratio_diff"]]
    if use_margin:
        # This is percentage where 100% = (100% + SCOUT_MARGIN)
        # percent = (x.ratio + 1) * (1 + config.SCOUT_MARGIN / 100) * 100
        percent = (x["ratio_diff"] + 1) * 100
        l.append(f"{percent:.2f}%")
    ratio_dict_out.append(l)

header = ["To coin", "Ratio"]

print(f"Current coin: {current_coin}")
print(f"Last update time: {last_time}")

if use_margin:
    scout_margin = float(config.get("binance_user_config", "scout_margin"))
    header.append("next jump")
    print(f"Scout margin: {scout_margin}% (jump on perc. accum. ~ {100 + scout_margin / 100}%)")

print(tabulate(ratio_dict_out, headers=header, tablefmt="github", numalign="center", stralign="center", floatfmt=".2f"))
