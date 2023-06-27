import demo_nft_marketplace.models as models
from demo_nft_marketplace.types.hen_minter.tezos_parameters.collect import CollectParameter
from demo_nft_marketplace.types.hen_minter.tezos_storage import HenMinterStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktTransaction


async def on_collect(
    ctx: HandlerContext,
    collect: TzktTransaction[CollectParameter, HenMinterStorage],
) -> None:
    swap = await models.Swap.filter(id=collect.parameter.swap_id).get()
    seller = await swap.creator
    buyer, _ = await models.Holder.get_or_create(address=collect.data.sender_address)

    trade = models.Trade(
        swap=swap,
        seller=seller,
        buyer=buyer,
        amount=int(collect.parameter.objkt_amount),
        level=collect.data.level,
        timestamp=collect.data.timestamp,
    )
    await trade.save()

    swap.amount_left -= int(collect.parameter.objkt_amount)
    if swap.amount_left == 0:
        swap.status = models.SwapStatus.FINISHED
    await swap.save()