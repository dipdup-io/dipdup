import demo_auction.models as models
from demo_auction.types.tzcolors_auction.parameter.bid import BidParameter
from demo_auction.types.tzcolors_auction.storage import TzcolorsAuctionStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import Transaction


async def on_bid(
    ctx: HandlerContext,
    bid: Transaction[BidParameter, TzcolorsAuctionStorage],
) -> None:
    assert bid.data.amount is not None

    auction = await models.Auction.filter(
        id=bid.parameter.__root__,
    ).get()

    bidder, _ = await models.User.get_or_create(address=bid.data.sender_address)
    await models.Bid(
        auction=auction,
        bidder=bidder,
        bid_amount=bid.data.amount,
        level=bid.data.level,
        timestamp=bid.data.timestamp,
    ).save()

    auction.bidder = bidder
    auction.bid_amount += bid.data.amount
    await auction.save()
