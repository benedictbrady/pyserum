import sys

sys.path.append("/Users/benedictbrady/code/pyserum")
sys.path.append("/Users/benedictbrady/code/solana-py/src")
import asyncio
import logging
from timeit import default_timer as timer

from solana.rpc.websocket_api import connect

from pyserum.async_connection import async_conn
from pyserum.connection import get_live_markets
from pyserum.market import AsyncMarket, AsyncWebsocketMarket

MILLISECONDS_IN_SECONDS = 1_000


class SerumMarketData:
    def __init__(self, ticker, url_stub="api.mainnet-beta.solana.com"):
        self.ticker = ticker
        self.url_stub = url_stub
        self.serum_ticker = self._get_serum_ticker()
        self.address = self._get_address()
        self.cumulative_bid = None
        self.cumulative_ask = None

    def _get_serum_ticker(self):
        assert "_" in self.ticker, "Invalid ticker"
        base, counter = self.ticker.split("_")
        return f"{base}/{counter}"

    def _get_address(self):
        for pair in get_live_markets():
            if pair.name == self.serum_ticker:
                return pair.address

    async def print_book(self):
        async with async_conn(f"https://{self.url_stub}") as connection:
            market = await AsyncMarket.load(connection, self.address)
            asks = await market.load_asks()
            bids = await market.load_bids()
            for bid in bids:
                print(f"BID | Order id: {bid.order_id}, price: {bid.info.price}, size: {bid.info.size}")
            for ask in asks:
                print(f"ASK | Order id: {ask.order_id}, price: {ask.info.price}, size: {ask.info.size}")

    @staticmethod
    def _wrap_book_iterable(book, side):
        if side == "bid":
            return iter(reversed(list(book)))
        if side == "ask":
            return iter(book)

        raise Exception(f"Invalid side {side}")

    @staticmethod
    def compute_cumulative_price(book_iterable, quantity):
        cumulative_quantity = 0
        while cumulative_quantity < quantity:
            order = next(book_iterable)
            price = order.info.price
            size = order.info.size
            cumulative_quantity += size
        return price

    async def stream_cumulative_bid(self, quantity):
        async with async_conn(f"https://{self.url_stub}") as connection:
            market = await AsyncWebsocketMarket.initialize(connection, self.address)
            async with connect(f"wss://{self.url_stub}") as websocket:
                await market.subscribe_to_bids(websocket)
                try:
                    while True:
                        bids = await market.recv_bids(websocket)
                        start = timer()
                        bid_iterable = self._wrap_book_iterable(bids, "bid")
                        cumulative_bid = self.compute_cumulative_price(bid_iterable, quantity)
                        self.cumulative_bid = cumulative_bid
                        end = timer()
                        logging.info(
                            f"bid: {self.cumulative_bid} - ask: {self.cumulative_ask} | duration: {(end - start) * MILLISECONDS_IN_SECONDS}"
                        )
                except KeyboardInterrupt:
                    await market.unsubscribe_to_bids(websocket)
                    print("bid websocket shutdown properly")

    async def stream_cumulative_ask(self, quantity):
        async with async_conn(f"https://{self.url_stub}") as connection:
            market = await AsyncWebsocketMarket.initialize(connection, self.address)
            async with connect(f"wss://{self.url_stub}") as websocket:
                await market.subscribe_to_asks(websocket)
                try:
                    while True:
                        asks = await market.recv_asks(websocket)
                        start = timer()
                        ask_iterable = self._wrap_book_iterable(asks, "ask")
                        cumulative_ask = self.compute_cumulative_price(ask_iterable, quantity)
                        self.cumulative_ask = cumulative_ask
                        end = timer()
                        logging.info(
                            f"bid: {self.cumulative_bid} - ask: {self.cumulative_ask} | duration: {(end - start) * MILLISECONDS_IN_SECONDS}"
                        )
                except KeyboardInterrupt:
                    await market.unsubscribe_to_asks(websocket)
                    print("ask websocket shutdown properly")


if __name__ == "__main__":
    logging.basicConfig(filename="data.log", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)

    md = SerumMarketData("MSOL_USDC", url_stub="ssc-dao.genesysgo.net")
    print(md.address)
    # quantity = 0.001
    # loop = asyncio.get_event_loop()
    # asyncio.ensure_future(md.stream_cumulative_bid(quantity))
    # asyncio.ensure_future(md.stream_cumulative_ask(quantity))
    # loop.run_forever()
    asyncio.run(md.print_book())
