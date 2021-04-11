from dipdup_hic_et_nunc.models import *
from dipdup_hic_et_nunc.types.KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9.parameter.mint_OBJKT import MintOBJKT
from dipdup_hic_et_nunc.types.KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton.parameter.mint import Mint

from dipdup.models import HandlerContext, OperationContext


async def on_mint(
    ctx: HandlerContext,
    mint_objkt: OperationContext[MintOBJKT],
    mint: OperationContext[Mint],
) -> None:
    ...
