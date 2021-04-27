import demo_tzcolors.models as models
from demo_tzcolors.types.tzcolors_auction.parameter.create_auction import CreateAuction as CreateAuctionParameter
from demo_tzcolors.types.tzcolors_auction.storage import Storage as TzcolorsAuctionStorage
from dipdup.models import OperationHandlerContext, OperationContext


async def on_create_auction(
    ctx: OperationHandlerContext,
    create_auction: OperationContext[CreateAuctionParameter, TzcolorsAuctionStorage],
) -> None:

    holder, _ = await models.Address.get_or_create(address=create_auction.data.sender_address)

    token, _ = await models.Token.get_or_create(
        id=create_auction.parameter.token_id,
        address=create_auction.parameter.token_address,
        defaults=dict(
            amount=create_auction.parameter.token_amount,
            holder=holder,
            level=create_auction.data.level,
            timestamp=create_auction.data.timestamp,
        ),
    )

    auction = models.Auction(
        id=create_auction.parameter.auction_id,
        token=token,
        bid_amount=create_auction.parameter.bid_amount,
        bidder=holder,
        seller=holder,
        end_timestamp=create_auction.parameter.end_timestamp,
        status=models.AuctionStatus.ACTIVE,
        level=create_auction.data.level,
        timestamp=create_auction.data.timestamp,
    )
    await auction.save()

    bid = models.Bid(
        auction=auction,
        bidder=holder,
        bid_amount=create_auction.parameter.bid_amount,
        level=create_auction.data.level,
        timestamp=create_auction.data.timestamp,
    )
    await bid.save()
