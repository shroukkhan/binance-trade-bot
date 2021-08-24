import abc
import asyncio
import concurrent.futures
import threading
import uuid
from collections import deque
from contextlib import asynccontextmanager, contextmanager, suppress
from typing import Callable, Dict, List, Optional, Set, Union

import binance.client
from binance.exceptions import BinanceAPIException
from sortedcontainers import SortedDict
from unicorn_binance_websocket_api import BinanceWebSocketApiManager

from .config import Config
from .logger import Logger


class ThreadSafeAsyncLock:
    def __init__(self):
        self._init_lock = threading.Lock()
        self._async_lock: Optional[asyncio.Lock] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def attach_loop(self):
        with self._init_lock:
            self._async_lock = asyncio.Lock()
            self.loop = asyncio.get_running_loop()

    def acquire(self):
        self.__enter__()

    def release(self):
        self.__exit__(None, None, None)

    def __enter__(self):
        self._init_lock.__enter__()
        if self._async_lock is not None:
            asyncio.run_coroutine_threadsafe(self._async_lock.__aenter__(), self.loop).result()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._async_lock is not None:
            asyncio.run_coroutine_threadsafe(self._async_lock.__aexit__(exc_type, exc_val, exc_tb), self.loop).result()
        self._init_lock.__exit__(exc_type, exc_val, exc_tb)

    async def __aenter__(self):
        await self._async_lock.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._async_lock.__aexit__(exc_type, exc_val, exc_tb)


class BinanceOrder:  # pylint: disable=too-few-public-methods
    def __init__(self, report):
        self.symbol = report["symbol"]
        self.side = report["side"]
        self.order_type = report["type"]
        self.id = report["orderId"]
        self.cumulative_quote_qty = float(report["cummulativeQuoteQty"])
        self.status = report["status"]
        self.price = float(report["price"])
        self.time = report["transactTime"]
        self.cumulative_filled_quantity = float(report["executedQty"])

    def __repr__(self):
        return f"<BinanceOrder {self.__dict__}>"


class BinanceCache:  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.ticker_values: Dict[str, float] = {}
        self._balances: Dict[str, float] = {}
        self._balances_mutex: ThreadSafeAsyncLock = ThreadSafeAsyncLock()
        self.non_existent_tickers: Set[str] = set()
        self.balances_changed_event = threading.Event()

    def attach_loop(self):
        self._balances_mutex.attach_loop()

    @contextmanager
    def open_balances(self):
        with self._balances_mutex:
            yield self._balances

    @asynccontextmanager
    async def open_balances_async(self):
        async with self._balances_mutex:
            yield self._balances


class DepthCache:
    def __init__(self, keep_limit=200, max_size=400):
        """Initialise the DepthCache

        :param keep_limit: How many items to keep in each dict after wipe
        :type keep_limit: int
        :param max_size: Max size of dict after which wipe occurs
        :type max_size: int

        """
        self.bids = SortedDict()
        self.asks = SortedDict()
        self.keep_limit = keep_limit
        self.max_size = max_size

    def add_bid(self, bid):
        """Add a bid to the cache

        :param bid:
        :return:

        """
        price = float(bid[0])
        amount = self.bids[price] = float(bid[1])
        if amount == 0:
            del self.bids[price]
        elif len(self.bids) >= self.max_size:
            self.bids = SortedDict({k: self.bids[k] for k in self.bids.keys()[-self.keep_limit :]})

    def add_ask(self, ask):
        """Add an ask to the cache

        :param ask:
        :return:

        """
        price = float(ask[0])
        amount = self.asks[price] = float(ask[1])
        if amount == 0:
            del self.asks[price]
        elif len(self.asks) >= self.max_size:
            self.asks = SortedDict({k: self.asks[k] for k in self.asks.keys()[: self.keep_limit]})

    def get_bids(self):
        """Get the current bids

        :return: list of bids with price and quantity as conv_type

        .. code-block:: python

            [
                [
                    0.0001946,  # Price
                    45.0        # Quantity
                ],
                [
                    0.00019459,
                    2384.0
                ],
                [
                    0.00019158,
                    5219.0
                ],
                [
                    0.00019157,
                    1180.0
                ],
                [
                    0.00019082,
                    287.0
                ]
            ]

        """
        return reversed(self.bids.items())

    def get_asks(self):
        """Get the current asks

        :return: list of asks with price and quantity as conv_type.

        .. code-block:: python

            [
                [
                    0.0001955,  # Price
                    57.0'       # Quantity
                ],
                [
                    0.00019699,
                    778.0
                ],
                [
                    0.000197,
                    64.0
                ],
                [
                    0.00019709,
                    1130.0
                ],
                [
                    0.0001971,
                    385.0
                ]
            ]

        """
        return self.asks.items()

    def clear(self):
        self.bids.clear()
        self.asks.clear()


class DepthCacheManager:
    def __init__(self, symbol, client: binance.AsyncClient, logger: Logger, limit=100):
        self.id = uuid.uuid4()
        self.pending_signals_counter = 0
        self.pending_reinit = False
        self.data_queue = deque()
        self.symbol = symbol
        self.depth_cache = DepthCache()
        self.client = client
        self.limit = limit
        self.last_update_id = -1
        self.logger = logger

    async def _handle_data(self, data):
        if data["final_update_id_in_event"] <= self.last_update_id:
            return  # ignore
        if data["first_update_id_in_event"] > self.last_update_id + 1:
            self.logger.debug(
                f"OB: {self.symbol} reinit, update delta: {data['first_update_id_in_event'] - self.last_update_id}"
            )
            await self.reinit()
            return
        self.apply_orders(data)
        self.last_update_id = data["final_update_id_in_event"]

    def buffer_incoming_data(self) -> bool:
        return self.pending_signals_counter > 0 or self.pending_reinit

    async def process_data(self, data):
        if self.buffer_incoming_data():
            self.data_queue.append(data)
            return

        while len(self.data_queue) > 0:
            pop_data = self.data_queue.popleft()
            await self._handle_data(pop_data)
        await self._handle_data(data)

    def apply_orders(self, msg):
        for bid in msg["bids"]:
            self.depth_cache.add_bid(bid)
        for ask in msg["asks"]:
            self.depth_cache.add_ask(ask)

    async def reinit(self):
        self.pending_reinit = True
        self.depth_cache.clear()
        while True:
            try:
                res = await self.client.get_order_book(symbol=self.symbol, limit=self.limit)
            except BinanceAPIException as e:
                self.logger.error(f"Error while fetching snapshot of order book: {e}")
                await asyncio.sleep(0.5)
            else:
                break
        self.apply_orders(res)
        self.last_update_id = res["lastUpdateId"]
        self.pending_reinit = False

    async def process_signal(self, signal):
        if signal["type"] == "CONNECT":
            self.logger.debug(f"OB: CONNECT arrived for symbol {self.symbol}")
            await self.reinit()
        elif signal["type"] == "DISCONNECT":
            self.logger.debug(f"OB: DISCONNECT arrived for symbol {self.symbol}")
            self.depth_cache.clear()
        self.pending_signals_counter -= 1
        assert self.pending_signals_counter >= 0

    def notify_pending_signal(self):
        self.pending_signals_counter += 1


class AsyncListenerContext:
    def __init__(
        self,
        buffer_names: List[str],
        cache: BinanceCache,
        logger: Logger,
        client: binance.AsyncClient,
        depth_cache_managers: Dict[str, DepthCacheManager],
    ):
        self.queues: Dict[str, asyncio.Queue] = {name: asyncio.Queue() for name in buffer_names}
        self.loop = asyncio.get_running_loop()
        self.buffer_names = buffer_names
        self.cache = cache
        self.logger = logger
        self.resolver = None
        self.stopped = False
        self.client = client
        self.depth_cache_managers = depth_cache_managers
        self.replace_signals = {"CONNECT": set(), "DISCONNECT": set()}

    def attach_stream_uuid_resolver(self, resolver: Callable[[uuid.UUID], str]):
        self.resolver = resolver

    def notify_stream_replace(self, old_stream_id: uuid.UUID, new_stream_id: uuid.UUID):
        self.replace_signals["CONNECT"].add(new_stream_id)
        self.replace_signals["DISCONNECT"].add(old_stream_id)

    def resolve_stream_id(self, stream_id: uuid.UUID) -> str:
        return self.resolver(stream_id)

    def add_stream_data(self, stream_data, stream_buffer_name: Union[str, bool] = False):
        if self.stopped:
            return
        asyncio.run_coroutine_threadsafe(self.queues[stream_buffer_name].put(stream_data), self.loop)

    async def get_market_sell_price_fill_quote(self, symbol: str, quote: float):
        depth_cache = self.depth_cache_managers[symbol].depth_cache
        amount = 0.0
        unfilled_quote = quote
        filled = False
        if abs(quote) <= 1e-15:
            return 0.0, 0.0
        for (price, bid_amount) in reversed(depth_cache.bids.items()):
            curr_amount = unfilled_quote / price
            fill = min(bid_amount, curr_amount)
            amount += fill
            unfilled_quote -= price * fill
            if abs(unfilled_quote) <= 1e-15:
                filled = True
                break
        if not filled:
            return None, None
        return quote / amount, amount

    async def get_market_sell_price(self, symbol: str, amount: float):
        depth_cache = self.depth_cache_managers[symbol].depth_cache
        quote = 0.0
        unfilled_amount = amount
        filled = False
        if abs(amount) <= 1e-15:
            return 0.0, 0.0
        for (price, bid_amount) in reversed(depth_cache.bids.items()):
            fill = min(bid_amount, unfilled_amount)
            quote += price * fill
            unfilled_amount -= fill
            if abs(unfilled_amount) <= 1e-15:
                filled = True
                break
        if not filled:
            return None, None
        return quote / amount, quote

    async def get_market_buy_price(self, symbol: str, quote_amount: float):
        depth_cache = self.depth_cache_managers[symbol].depth_cache
        amount = 0.0
        unfilled_quote = quote_amount
        filled = False
        if abs(quote_amount) <= 1e-15:
            return 0.0, 0.0
        for (price, ask_amount) in depth_cache.asks.items():
            curr_amount = unfilled_quote / price
            fill = min(curr_amount, ask_amount)
            amount += fill
            unfilled_quote -= fill * price
            if abs(unfilled_quote) <= 1e-15:
                filled = True
                break
        if not filled:
            return None, None
        return quote_amount / amount, amount

    def add_signal_data(self, signal_data: Dict):
        if self.stopped:
            return
        stream_id = signal_data["stream_id"]
        buffer_name = self.resolver(stream_id)
        asyncio.run_coroutine_threadsafe(self.queues[buffer_name].put(signal_data), self.loop)

    async def shutdown(self):
        self.logger.debug("prepare graceful loop shutdown")
        self.stopped = True
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.debug("loop shutdown")
        self.resolver = None  # to prevent circular ref
        self.loop.stop()


class AppendProxy:
    def __init__(self, append_proxy_func):
        self.append_proxy_func = append_proxy_func

    def append(self, obj):
        self.append_proxy_func(obj)

    def pop(self):  # pylint: disable=no-self-use
        return None


class AsyncListenedBWAM(BinanceWebSocketApiManager):
    def __init__(self, async_listener_context: AsyncListenerContext, *args, **kwargs):
        self.async_listener_context = async_listener_context
        super().__init__(*args, process_stream_data=self.async_listener_context.add_stream_data, **kwargs)
        self.stream_signal_buffer = AppendProxy(self.async_listener_context.add_signal_data)
        self.async_listener_context.attach_stream_uuid_resolver(self.stream_uuid_resolver)

    def stream_uuid_resolver(self, stream_id: uuid.UUID):
        return self.stream_list[stream_id]["stream_buffer_name"]

    def stop_manager_with_all_streams(self):
        super().stop_manager_with_all_streams()
        asyncio.run_coroutine_threadsafe(self.async_listener_context.shutdown(), self.async_listener_context.loop)


BUFFER_NAME_MINITICKERS = "mt"
BUFFER_NAME_USERDATA = "ud"
BUFFER_NAME_DEPTH = "de"


class LoopExecutor(abc.ABC):  # pylint:disable=too-few-public-methods
    @abc.abstractmethod
    async def run_loop(self):
        ...


class AsyncListener(LoopExecutor):
    def __init__(self, buffer_name: str, async_context: AsyncListenerContext):
        self.buffer_name = buffer_name
        self.async_context = async_context

    @staticmethod
    def is_stream_signal(obj):
        return "type" in obj

    async def handle_signal(self, signal):  # pylint: disable=unused-argument
        ...

    async def handle_data(self, data):  # pylint: disable=unused-argument
        ...

    async def run_loop(self):
        while True:
            data = await self.async_context.queues[self.buffer_name].get()

            if AsyncListener.is_stream_signal(data):
                signal_type = data["type"]
                if signal_type in self.async_context.replace_signals:
                    stream_id = data["stream_id"]
                    if stream_id in self.async_context.replace_signals[signal_type]:
                        self.async_context.replace_signals[signal_type].remove(stream_id)
                        self.async_context.logger.debug(f"skip {signal_type} signal for {self.buffer_name}")
                        self.async_context.logger.debug(
                            [(sig, len(x)) for sig, x in self.async_context.replace_signals.items()]
                        )
                        continue
                await self.handle_signal(data)
            else:
                await self.handle_data(data)


class TickerListener(AsyncListener):
    def __init__(self, async_context: AsyncListenerContext):
        super().__init__(BUFFER_NAME_MINITICKERS, async_context)

    async def handle_data(self, data):
        if "event_type" in data:
            if data["event_type"] == "24hrMiniTicker":
                for event in data["data"]:
                    self.async_context.cache.ticker_values[event["symbol"]] = float(event["close_price"])
            else:
                self.async_context.logger.error(f"Unknown event type found: {data}")


class UserDataListener(AsyncListener):
    def __init__(self, async_context: AsyncListenerContext):
        super().__init__(BUFFER_NAME_USERDATA, async_context)

    async def handle_data(self, data):
        if "event_type" in data:
            event_type = data["event_type"]
            # We ignore execution reports because market orders are always filled
            if event_type == "balanceUpdate":
                self.async_context.logger.debug(f"Balance update: {data}")
                async with self.async_context.cache.open_balances_async() as balances:
                    asset = data["asset"]
                    if asset in balances:
                        del balances[data["asset"]]
                    self.async_context.cache.balances_changed_event.set()
            elif event_type in ("outboundAccountPosition", "outboundAccountInfo"):
                self.async_context.logger.debug(f"{event_type}: {data}")
                async with self.async_context.cache.open_balances_async() as balances:
                    for bal in data["balances"]:
                        balances[bal["asset"]] = float(bal["free"])
                    self.async_context.cache.balances_changed_event.set()

    async def _invalidate_balances(self):
        async with self.async_context.cache.open_balances_async() as balances:
            balances.clear()
            self.async_context.cache.balances_changed_event.set()

    async def handle_signal(self, signal):
        signal_type = signal["type"]
        if signal_type == "CONNECT":
            self.async_context.logger.debug("Connect for userdata arrived", False)
            await self._invalidate_balances()


class DepthListener(AsyncListener):
    def __init__(self, async_context: AsyncListenerContext, depth_cache_managers: Dict[str, DepthCacheManager]):
        super().__init__(BUFFER_NAME_DEPTH, async_context)
        self.depth_cache_managers = depth_cache_managers

    async def handle_data(self, data):
        if "symbol" in data:
            await self.depth_cache_managers[data["symbol"]].process_data(data)

    async def handle_signal(self, signal):
        dcms = self.depth_cache_managers.values()
        for dcm in dcms:  # switch every dcm to backpressure
            dcm.notify_pending_signal()
        await asyncio.wait([asyncio.create_task(dcm.process_signal(signal)) for dcm in dcms])


class BinanceStreamManager:
    def __init__(
        self,
        logger: Logger,
        async_context: AsyncListenerContext,
        bwam: AsyncListenedBWAM,
        execution_thread: threading.Thread,
    ):
        self.logger = logger
        self.bwam: AsyncListenedBWAM = bwam
        self.async_context: AsyncListenerContext = async_context
        self.execution_thread = execution_thread

    def get_market_sell_price(self, symbol: str, amount: float):
        return asyncio.run_coroutine_threadsafe(
            self.async_context.get_market_sell_price(symbol, amount), self.async_context.loop
        ).result()

    def get_market_buy_price(self, symbol: str, quote_amount: float):
        return asyncio.run_coroutine_threadsafe(
            self.async_context.get_market_buy_price(symbol, quote_amount), self.async_context.loop
        ).result()

    def close(self):
        self.bwam.stop_manager_with_all_streams()

    def get_market_sell_price_fill_quote(self, symbol: str, quote_amount: float):
        return asyncio.run_coroutine_threadsafe(
            self.async_context.get_market_sell_price_fill_quote(symbol, quote_amount), self.async_context.loop
        ).result()


class AutoReplacingStream(LoopExecutor):  # pylint:disable=too-few-public-methods
    def __init__(
        self,
        bwam: BinanceWebSocketApiManager,
        context: AsyncListenerContext,
        channels,
        markets,
        api_key: Union[str, bool] = False,
        api_secret: Union[str, bool] = False,
        stream_buffer_name: Union[str, bool] = False,
        restart_every=60 * 60,
    ):  # pylint:disable=too-many-arguments
        self.context = context
        self.restart_every = restart_every
        self.bwam = bwam
        self.channels = channels
        self.markets = markets
        self.api_key = api_key
        self.api_secret = api_secret
        self.stream_buffer_name = stream_buffer_name
        self.last_stream_id = self.bwam.create_stream(
            channels, markets, api_key=api_key, api_secret=api_secret, stream_buffer_name=stream_buffer_name
        )

    async def run_loop(self):
        while True:
            if self.bwam.is_manager_stopping():
                return
            await asyncio.sleep(self.restart_every)

            old_stream_id = self.last_stream_id
            self.last_stream_id = self.bwam.replace_stream(
                self.last_stream_id,
                self.channels,
                self.markets,
                new_stream_buffer_name=self.stream_buffer_name,
                new_api_key=self.api_key,
                new_api_secret=self.api_secret,
                new_output="UnicornFy",
            )
            self.context.notify_stream_replace(old_stream_id, self.last_stream_id)


class StreamManagerWorker(threading.Thread):
    def __init__(self, cache: BinanceCache, config: Config, logger: Logger, fut: concurrent.futures.Future):
        super().__init__()
        self.cache = cache
        self.config = config
        self.logger = logger
        self.fut = fut

    async def arun(self):
        self.cache.attach_loop()
        client = await binance.AsyncClient.create(
            self.config.BINANCE_API_KEY, self.config.BINANCE_API_SECRET_KEY, tld=self.config.BINANCE_TLD
        )
        depth_markets = [coin.lower() + self.config.BRIDGE.symbol.lower() for coin in self.config.SUPPORTED_COIN_LIST]
        depth_cache_managers = {
            symbol.upper(): DepthCacheManager(symbol.upper(), client, self.logger) for symbol in depth_markets
        }
        async_context = AsyncListenerContext(
            [BUFFER_NAME_MINITICKERS, BUFFER_NAME_USERDATA, BUFFER_NAME_DEPTH],
            self.cache,
            self.logger,
            client,
            depth_cache_managers,
        )
        bwam = AsyncListenedBWAM(
            async_context,
            output_default="UnicornFy",
            enable_stream_signal_buffer=True,
            exchange=f"binance.{self.config.BINANCE_TLD}",
        )
        quotes = set(map(str.lower, [self.config.BRIDGE.symbol, "usdt", "btc", "bnb"]))
        markets = [coin.lower() + quote for quote in quotes for coin in self.config.SUPPORTED_COIN_LIST]
        restart_every = 3600 * 4
        streams: List[LoopExecutor] = [
            AutoReplacingStream(
                bwam,
                async_context,
                ["miniTicker"],
                markets,
                stream_buffer_name=BUFFER_NAME_MINITICKERS,
                restart_every=restart_every,
            ),
            AutoReplacingStream(
                bwam,
                async_context,
                ["depth@100ms"],
                depth_markets,
                stream_buffer_name=BUFFER_NAME_DEPTH,
                restart_every=restart_every,
            ),
        ]
        bwam.create_stream(
            ["arr"],
            ["!userData"],
            api_key=self.config.BINANCE_API_KEY,
            api_secret=self.config.BINANCE_API_SECRET_KEY,
            stream_buffer_name=BUFFER_NAME_USERDATA,
        )
        listeners: List[LoopExecutor] = [
            TickerListener(async_context),
            UserDataListener(async_context),
            DepthListener(async_context, depth_cache_managers),
        ]
        executors: List[LoopExecutor] = listeners + streams
        stream_manager = BinanceStreamManager(self.logger, async_context, bwam, self)
        self.fut.set_result(stream_manager)
        await asyncio.gather(*[executable.run_loop() for executable in executors])

    def run(self):
        with suppress(asyncio.CancelledError):
            asyncio.run(self.arun())

    @staticmethod
    def create(cache: BinanceCache, config: Config, logger: Logger) -> BinanceStreamManager:
        fut = concurrent.futures.Future()
        execution_thread = StreamManagerWorker(cache, config, logger, fut)
        execution_thread.start()
        return fut.result()
