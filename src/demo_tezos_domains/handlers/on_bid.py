import demo_tezos_domains.models as models
from demo_tezos_domains.types.tld_registrar.parameter.execute import Execute as RegistrarExecute
from demo_tezos_domains.types.tld_registrar_bid.parameter.bid import Bid
from dipdup.models import HandlerContext, OperationContext


async def on_bid(
    ctx: HandlerContext,
    bid: OperationContext[Bid],
    registrar_execute: OperationContext[RegistrarExecute],
) -> None:
    assert registrar_execute.storage
    bidder, _ = await models.Address.get_or_create(address=bid.data.sender_address)
    label = bid.parameter.label
    ownership_period = registrar_execute.storage.store.auctions[label].ownership_period
    ends_at = registrar_execute.storage.store.auctions[label].ends_at
    auction, _ = await models.Auction.get_or_create(
        label=label,
        defaults=dict(
            status=models.AuctionStatus.ACTIVE,
            ownership_period=ownership_period,
            ends_at=ends_at,
        ),
    )
    bid_model = models.Bid(
        bidder=bidder,
        auction=auction,
        bid=bid.parameter.bid,
    )
    await bid_model.save()
