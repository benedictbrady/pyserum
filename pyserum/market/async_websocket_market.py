"""Market module to interact with Serum DEX."""
from __future__ import annotations

from typing import List

from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import RPCResponse, TxOpts
from solana.transaction import Transaction
from solana.rpc.websocket_api import SolanaWsClientProtocol

import pyserum.market.types as t
from pyserum import instructions

from .._layouts.open_orders import OPEN_ORDERS_LAYOUT
from ..async_open_orders_account import AsyncOpenOrdersAccount
from ..async_websocket_utils import load_bytes_data
from ..enums import OrderType, Side
from ._internal.queue import decode_event_queue, decode_request_queue
from .core import MarketCore
from .orderbook import OrderBook
from .state import MarketState


LAMPORTS_PER_SOL = 1000000000


# pylint: disable=too-many-public-methods,abstract-method
class AsyncWebsocketMarket(MarketCore):
    """Represents a Serum Market."""

    def __init__(self, conn: AsyncClient, market_state: MarketState, market_address: PublicKey, force_use_request_queue: bool = False) -> None:
        super().__init__(market_state=market_state, force_use_request_queue=force_use_request_queue)
        self._conn = conn
        self.bid_address = market_state.bids()
        self.ask_address = market_state.asks()
        self.market_address = market_address
        self.bid_subscription_id = None
        self.ask_subscription_id = None

    @classmethod
    # pylint: disable=unused-argument
    async def initialize(
        cls,
        conn: AsyncClient,
        market_address: PublicKey,
        program_id: PublicKey = instructions.DEFAULT_DEX_PROGRAM_ID,
        force_use_request_queue: bool = False,
    ) -> AsyncWebsocketMarket:
        """Factory method to create a Market.

        :param conn: The connection that we use to load the data, created from `solana.rpc.api`.
        :param market_address: The market address that you want to connect to.
        :param program_id: The program id of the given market, it will use the default value if not provided.
        """
        market_state = await MarketState.async_load(conn, market_address, program_id)
        return cls(conn, market_state, market_address, force_use_request_queue)

    async def subscribe_to_bids(self, websocket) -> None:
        """Subscribe to bid order book"""
        await websocket.account_subscribe(pubkey=self.bid_address, encoding="jsonParsed")
        resp = await websocket.recv()
        subscription_id = resp.result
        self.bid_subscription_id = subscription_id
        print(f"bid feed subscribed: {self.bid_subscription_id}")
    
    async def subscribe_to_asks(self, websocket) -> None:
        """Subscribe to ask order book"""
        await websocket.account_subscribe(pubkey=self.ask_address, encoding="jsonParsed")
        resp = await websocket.recv()
        subscription_id = resp.result
        self.ask_subscription_id = subscription_id
        print(f"ask feed subscribed: {self.ask_subscription_id}")

    async def recv_bids(self, websocket) -> OrderBook:
        """Recieve another bid order book"""
        if self.bid_subscription_id:
            bytes_data = await load_bytes_data(websocket)
            return self._parse_bids_or_asks(bytes_data)
        else:
            raise Exception("Please subscribe to bid feed first")

    async def recv_asks(self, websocket) -> OrderBook:
        """Recieve another ask order book"""
        if self.ask_subscription_id:
            bytes_data = await load_bytes_data(websocket)
            return self._parse_bids_or_asks(bytes_data)
        else:
            raise Exception("Please subscribe to ask feed first")

    async def unsubscribe_to_bids(self, websocket) -> None:
        """Unsubscribe from bid order book"""
        if self.bid_subscription_id:
            await websocket.account_unsubscribe(self.bid_subscription_id)
        else:
            raise Exception("Please subscribe to bid feed first")

    async def unsubscribe_to_asks(self, websocket) -> None:
        """Unsubscribe from ask order book"""
        if self.ask_subscription_id:
            await websocket.account_unsubscribe(self.ask_subscription_id)
        else:
            raise Exception("Please subscribe to ask feed first")
