from demo_hic_et_nunc.models import *
from demo_hic_et_nunc.types.hen_minter.parameter.mint_objkt import MintOBJKT
from demo_hic_et_nunc.types.hen_objkts.parameter.mint import Mint
from dipdup.models import HandlerContext, OperationContext


async def on_mint(
    ctx: HandlerContext,
    mint_objkt: OperationContext[MintOBJKT],
    mint: OperationContext[Mint],
) -> None:
    ...
