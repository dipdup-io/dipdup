import demo_auction.models as models
from demo_auction.types.tzcolors_auction.tezos_parameters.withdraw import WithdrawParameter
from demo_auction.types.tzcolors_auction.tezos_storage import TzcolorsAuctionStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktTransaction


async def on_withdraw(
    ctx: HandlerContext,
    withdraw: TzktTransaction[WithdrawParameter, TzcolorsAuctionStorage],
) -> None:
    auction = await models.Auction.filter(
        id=withdraw.parameter.__root__,
    ).get()

    # FIXME: Don't do that, returns None when id=0. Bug in Tortoise?
    # token = await auction.token
    token = await models.Token.filter(id=auction.token_id).get()

    token.holder = await auction.bidder
    await token.save()

    auction.status = models.AuctionStatus.FINISHED
    await auction.save()
