import demo_tezos_nft_marketplace.models as models
from demo_tezos_nft_marketplace.types.hen_minter.tezos_parameters.cancel_swap import CancelSwapParameter
from demo_tezos_nft_marketplace.types.hen_minter.tezos_storage import HenMinterStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosTransaction


async def on_cancel_swap(
    ctx: HandlerContext,
    cancel_swap: TezosTransaction[CancelSwapParameter, HenMinterStorage],
) -> None:
    swap = await models.Swap.filter(id=int(cancel_swap.parameter.root)).get()
    swap.status = models.SwapStatus.CANCELED
    await swap.save()
