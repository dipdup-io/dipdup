from dipdup.models import HandlerContext, OperationContext

import demo_tzcolors.models as models

from demo_tzcolors.types.tzcolors_auction.parameter.create_auction import CreateAuction


async def on_create_auction(
    ctx: HandlerContext,
    create_auction: OperationContext[CreateAuction],
) -> None:

    holder, _ = await models.Address.get_or_create(address=create_auction.parameter.token_address)

    token = await models.Token.filter(
        id=create_auction.parameter.token_id,
    ).get()

    auction = models.Auction(
        id=create_auction.parameter.auction_id,
        token_address=token.address,
        token_id=token.id,
        token_amount=token.amount,
        bid_amount=create_auction.parameter.bid_amount,
        bidder=holder,
        seller=holder,
        end_timestamp=create_auction.parameter.end_timestamp,
        level=create_auction.data.level,
        timestamp=create_auction.data.timestamp,
    )
    await auction.save()

    bid = models.Bid(
        token_id=token.id,
        bidder=holder,
        level=create_auction.data.level,
        timestamp=create_auction.data.timestamp,
    )
    await bid.save()