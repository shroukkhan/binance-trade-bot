import queue
import threading
from os import path

import apprise

APPRISE_CONFIG_PATH = "config/apprise.yml"


class NotificationHandler:
    """
    A class that handles notifications.

    Args:
        enabled (bool, optional): Whether the notification handler is enabled. Defaults to True.

    Attributes:
        apobj (apprise.Apprise): An instance of the Apprise class.
        queue (queue.Queue): A queue to store notification messages and attachments.
        enabled (bool): Whether the notification handler is enabled.

    """

    def __init__(self, enabled=True):
        """
        Initializes a new instance of the NotificationHandler class.

        Args:
            enabled (bool, optional): Whether the notification handler is enabled. Defaults to True.

        """
        if enabled and path.exists(APPRISE_CONFIG_PATH):
            self.apobj = apprise.Apprise()
            config = apprise.AppriseConfig()
            config.add(APPRISE_CONFIG_PATH)
            self.apobj.add(config)
            self.queue = queue.Queue()
            self.start_worker()
            self.enabled = True
        else:
            self.enabled = False

    def start_worker(self):
        """
        Starts a worker thread to process the notification queue.

        """
        threading.Thread(target=self.process_queue, daemon=True).start()

    def process_queue(self):
        """
        Processes the notification queue by sending notifications.

        """
        while True:
            message, attachments = self.queue.get()
            if attachments:
                self.apobj.notify(body=message, attach=attachments)

            else:
                self.apobj.notify(body=message)

        self.queue.task_done()

    def send_notification(self, message, attachments=None):
        """
        Sends a notification with the given message and attachments.

        Args:
            message (str): The message of the notification.
            attachments (list[str], optional): The attachments of the notification. Defaults to None.

        """
        if self.enabled:
            self.queue.put((message, attachments or []))
