import demo_nft_marketplace.models as models
from demo_nft_marketplace.types.hen_minter.tezos_parameters.swap import SwapParameter
from demo_nft_marketplace.types.hen_minter.tezos_storage import HenMinterStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktTransaction


async def on_swap(
    ctx: HandlerContext,
    swap: TzktTransaction[SwapParameter, HenMinterStorage],
) -> None:
    holder, _ = await models.Holder.get_or_create(address=swap.data.sender_address)
    swap_model = models.Swap(
        id=int(swap.storage.swap_id) - 1,
        creator=holder,
        price=swap.parameter.xtz_per_objkt,
        amount=swap.parameter.objkt_amount,
        amount_left=swap.parameter.objkt_amount,
        status=models.SwapStatus.ACTIVE,
        level=swap.data.level,
        timestamp=swap.data.timestamp,
    )
    await swap_model.save()