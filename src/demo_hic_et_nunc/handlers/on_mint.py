import demo_hic_et_nunc.models as models
from demo_hic_et_nunc.types.hen_minter.parameter.mint_objkt import MintOBJKTParameter
from demo_hic_et_nunc.types.hen_minter.storage import HenMinterStorage
from demo_hic_et_nunc.types.hen_objkts.parameter.mint import MintParameter
from demo_hic_et_nunc.types.hen_objkts.storage import HenObjktsStorage
from dipdup.context import BigMapHandlerContext, HandlerContext, OperationHandlerContext
from dipdup.models import BigMapData, BigMapDiff, OperationData, Origination, Transaction


async def on_mint(
    ctx: OperationHandlerContext,
    mint_objkt: Transaction[MintOBJKTParameter, HenMinterStorage],
    mint: Transaction[MintParameter, HenObjktsStorage],
) -> None:
    holder, _ = await models.Holder.get_or_create(address=mint.parameter.address)
    token = models.Token(
        id=mint.parameter.token_id,
        creator=holder,
        supply=mint.parameter.amount,
        level=mint.data.level,
        timestamp=mint.data.timestamp,
    )
    await token.save()
