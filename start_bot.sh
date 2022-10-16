#!/bin/sh
set -e

#echo running database_warmup

#python database_warmup.py

#echo warmup done...starting bot

python -m binance_trade_bot
