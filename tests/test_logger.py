import logging
import os

import pytest

from binance_trade_bot.logger import Logger
from .common import infra  # type: ignore


@pytest.fixture(scope="function", params=["crypto_trading", "boba_boba"])
def createAndDeleteFile(infra, request):
    ln = request.param
    fn = os.path.join("logs", ln + ".log")
    abspath = os.path.abspath(fn)
    print(f'abspath: {abspath}')
    if os.path.exists(fn):
        print(f"removing {fn}")
        os.remove(fn)
    else:
        print(f"does not exist: {fn}")

    yield ln, fn

    if os.path.exists(fn):
        print(f"removing {fn} again!")
        os.remove(fn)


def test_file_logging(caplog, createAndDeleteFile):
    ln, fn = createAndDeleteFile

    logs = Logger(enable_notifications=False, logging_service=ln)
    logs.Logger.propagate = True

    assert os.path.exists(fn), "Log file not exists" ## this will fail because i disabled file logging . TODO: make it a config option  

    logs.error("rroorree")
    assert caplog.record_tuples == [(logs.Logger.name, logging.ERROR, "rroorree")]
    caplog.clear()

    logs.info("ooffnnii")
    assert caplog.record_tuples == [(logs.Logger.name, logging.INFO, "ooffnnii")]
    caplog.clear()

    logs.warning("ggnniinnrraaww")
    assert caplog.record_tuples == [(logs.Logger.name, logging.WARNING, "ggnniinnrraaww")]
    caplog.clear()

    assert os.path.exists(fn), "Log file not exists"
    logs.close()


@pytest.mark.xfail
def test_console_logging(capsys, createAndDeleteFile):  # bad case
    ln, fn = createAndDeleteFile

    logs = Logger(enable_notifications=True, logging_service=ln)

    assert os.path.exists(fn), "Log file not exists"

    logs.debug("gguubbeedd", notification=True)
    captured = capsys.readouterr()
    xml = str(captured)
    assert str(captured).find("DEBUG") > -1

    logs.log("guliguli", level="error", notification=True)
    captured = capsys.readouterr()
    assert str(captured).find("ERROR") > -1

    assert os.path.exists(fn), "Log file not exists"
