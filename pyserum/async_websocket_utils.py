import base64
from solana.publickey import PublicKey
from solana.rpc.websocket_api import SolanaWsClientProtocol
from spl.token.constants import WRAPPED_SOL_MINT
from solana.rpc.responses import AccountNotification
from pyserum.utils import parse_bytes_data, parse_mint_decimals


def parse_bytes_data(res: AccountNotification) -> bytes:
    data = res.result.value.data[0]
    return base64.decodebytes(data.encode("ascii"))

async def load_bytes_data(conn: SolanaWsClientProtocol) -> bytes:
    res = await conn.recv()
    return parse_bytes_data(res)
