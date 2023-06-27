import demo_nft_marketplace.models as models
from demo_nft_marketplace.types.hen_minter.tezos_parameters.cancel_swap import CancelSwapParameter
from demo_nft_marketplace.types.hen_minter.tezos_storage import HenMinterStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktTransaction


async def on_cancel_swap(
    ctx: HandlerContext,
    cancel_swap: TzktTransaction[CancelSwapParameter, HenMinterStorage],
) -> None:
    swap = await models.Swap.filter(id=int(cancel_swap.parameter.__root__)).get()
    swap.status = models.SwapStatus.CANCELED
    await swap.save()