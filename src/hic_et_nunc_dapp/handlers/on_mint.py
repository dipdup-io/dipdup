import logging
from gettext import translation

from hic_et_nunc_dapp.models import Address, Token
from hic_et_nunc_dapp.types.KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9.parameter.mint_OBJKT import MintOBJKT
from hic_et_nunc_dapp.types.KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton.parameter.mint import Mint
from pytezos_dapps.models import HandlerContext

logger = logging.getLogger(__name__)


async def on_mint(mint_objct: HandlerContext[MintOBJKT], mint: HandlerContext[Mint]):
    address, _ = await Address.get_or_create(address=mint.parameter.address)

    for _ in range(int(mint.parameter.amount)):
        token = Token(
            token_id=int(mint.parameter.token_id),
            token_info=mint.parameter.token_info[''],
            holder=address,
            transaction=mint.transaction,
        )
        await token.save()
