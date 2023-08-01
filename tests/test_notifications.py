import os
import time

import pytest
import yaml

from binance_trade_bot.notifications import NotificationHandler
from .common import infra  # type: ignore
from unittest.mock import MagicMock

APPRISE_CONFIG_PATH = "config/apprise.yml"


@pytest.fixture()
def generate_apprise_config(infra):
    """
    Fixture for generating an Apprise configuration file.

    Args:
        infra: The infrastructure fixture.

    Yields:
        None
    """
    data = {
        'version': 1,
        'urls': [
            'tgram://5092371024:AAGtfHjjxjW5X7OMtBx0TZXvBnJn3yX1HLw/1964979389'
        ]
    }
    with open(APPRISE_CONFIG_PATH, 'w') as f:
        yaml.dump(data, f)
        yield




@pytest.fixture(scope='function')
def notification_handler_enabled(generate_apprise_config):
    """
    Fixture for creating a NotificationHandler object with enabled=True.

    Args:
        generate_apprise_config: The generate_apprise_config fixture.

    Returns:
        NotificationHandler: A NotificationHandler object with enabled=True.
    """

    return NotificationHandler(enabled=True )


def test_notification_handler_initialization_disabled():
    """
    Test case for initializing a NotificationHandler object with enabled=False.

    It asserts that the NotificationHandler's enabled attribute is False.
    """
    notification_handler = NotificationHandler(False)
    assert not notification_handler.enabled


def test_notification_handler_initialization_enabled(notification_handler_enabled):
    """
    Test case for initializing a NotificationHandler object with enabled=True.

    It asserts that the NotificationHandler's enabled attribute is True,
    and that it has the "apobj" and "queue" attributes.
    """
    assert notification_handler_enabled.enabled
    assert hasattr(notification_handler_enabled, "apobj")
    assert hasattr(notification_handler_enabled, "queue")


def test_send_notification(notification_handler_enabled):
    """
    Test case for sending a notification using a NotificationHandler object.

    It asserts that the notification is added to the queue correctly.
    """
    message = "Test message"
    attachments = ["attachment.png"]

    notification_handler_enabled.send_notification(message, attachments)
    queue_item = notification_handler_enabled.queue.get()

    assert queue_item == (message, attachments)

def test_process_queue(notification_handler_enabled):
    """
    Test case for processing the queue of a NotificationHandler object.

    It asserts that the queue is processed correctly.
    """
    message = "Test message"
    attachments = ["attachment.png"]

    notification_handler_enabled.send_notification(message, attachments)
    # before msg is sent, queue shold not be empty
    assert notification_handler_enabled.queue.qsize() == 1
    time.sleep(1)
    # now queue should be empty
    assert notification_handler_enabled.queue.qsize() == 0
    