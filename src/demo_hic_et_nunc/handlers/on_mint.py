from demo_hic_et_nunc.models import Holder, Token
from demo_hic_et_nunc.types.hen_minter.parameter.mint_objkt import MintOBJKT
from demo_hic_et_nunc.types.hen_objkts.parameter.mint import Mint
from dipdup.models import HandlerContext, OperationContext


async def on_mint(
    ctx: HandlerContext,
    mint_objkt: OperationContext[MintOBJKT],
    mint: OperationContext[Mint],
) -> None:
    holder, _ = await Holder.get_or_create(address=mint.parameter.address)
    token = Token(
        id=mint.parameter.token_id,
        creator=holder,
        supply=mint.parameter.amount,
        level=mint.data.level,
        timestamp=mint.data.timestamp,
    )
    await token.save()
