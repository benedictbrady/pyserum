import sys
sys.path.append("/Users/benedictbrady/projects/pyserum")
sys.path.append("/Users/benedictbrady/projects/solana-py/src")
import asyncio
from pyserum.connection import conn
from pyserum.market import AsyncWebsocketMarket, AsyncMarket
from pyserum.connection import get_live_markets, get_token_mints
from timeit import default_timer as timer
from solana.rpc.websocket_api import connect
from spl.token.client import Token
from solana.keypair import Keypair
from solana.publickey import PublicKey
from spl.token.constants import TOKEN_PROGRAM_ID
import logging


MSOL_PUBLIC_KEY = PublicKey("mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So")


PRIVATE_KEY = b''


class SerumOrderEntry:
    def __init__(self, url="https://api.mainnet-beta.solana.com"):
        self.keypair = Keypair.from_secret_key(PRIVATE_KEY)
        self._conn = conn(url)


    def _get_mint_address(self, currency):
        if currency == "MSOL":
            return MSOL_PUBLIC_KEY
        for pair in get_token_mints():
            if pair.name == currency:
                return PublicKey(pair.address)

    def create_token(self, currency):
        return Token(self._conn,
                           pubkey=self._get_mint_address(currency),
                           program_id=TOKEN_PROGRAM_ID,
                           payer=self.keypair
                           )

    def create_token_account(self, token):
        quote_wallet = token.create_associated_token_account(self.keypair.public_key, skip_confirmation=False)
        print("quote wallet: ", str(quote_wallet))

    def run(self):
        token = self.create_token("MSOL")
        self.create_token_account(token)


if __name__ == "__main__":
    logging.basicConfig(filename='order.log', format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)
    SerumOrderEntry().run()
