import logging.handlers

from .notifications import NotificationHandler


class LogLevel:
    error = 1
    warning = 2
    info = 3
    debug = 4


class Logger:
    Logger = None
    NotificationHandler = None

    def __init__(self, logging_service="crypto_trading", enable_notifications=True, level=LogLevel.debug):
        # Logger setup
        self.Logger = logging.getLogger(f"{logging_service}_logger")
        self.Logger.setLevel(logging.DEBUG)
        self.Logger.propagate = False
        self.LogLevel = level
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        # default is "logs/crypto_trading.log"
        # fh = logging.FileHandler(f"logs/{logging_service}.log")
        # fh.setLevel(logging.DEBUG)
        # fh.setFormatter(formatter)
        # self.Logger.addHandler(fh)

        # logging to console
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        self.Logger.addHandler(ch)

        # notification handler
        self.NotificationHandler = NotificationHandler(enable_notifications)

    def close(self):
        for handler in self.Logger.handlers[:]:
            handler.close()

    def log(self, message, level="info", notification=True):

        if self.LogLevel >= LogLevel.info and level == "info":
            self.Logger.info(message)
        elif self.LogLevel >= LogLevel.warning and level == "warning":
            self.Logger.warning(message)
        elif self.LogLevel >= LogLevel.error and level == "error":
            self.Logger.error(message)
        elif self.LogLevel >= LogLevel.debug and level == "debug":
            self.Logger.debug(message)

        if notification and self.NotificationHandler.enabled:
            self.NotificationHandler.send_notification(str(message))

    def info(self, message, notification=True):
        self.log(message, "info", notification)

    def warning(self, message, notification=True):
        self.log(message, "warning", notification)

    def error(self, message, notification=True):
        self.log(message, "error", notification)

    def debug(self, message, notification=False):
        self.log(message, "debug", notification)
