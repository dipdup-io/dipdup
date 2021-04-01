from hic_et_nunc_dapp.models import *
from hic_et_nunc_dapp.types.KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9.parameter.mint_OBJKT import MintObjkt
from hic_et_nunc_dapp.types.KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton.parameter.mint import Mint
from pytezos_dapps.models import HandlerContext


async def on_mint(
    mint_OBJKT: HandlerContext[MintObjkt],
    mint: HandlerContext[Mint],
) -> None:
    ...
