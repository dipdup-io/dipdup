import demo_tezos_auction.models as models
from demo_tezos_auction.types.tzcolors_auction.tezos_parameters.withdraw import WithdrawParameter
from demo_tezos_auction.types.tzcolors_auction.tezos_storage import TzcolorsAuctionStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosTransaction


async def on_withdraw(
    ctx: HandlerContext,
    withdraw: TezosTransaction[WithdrawParameter, TzcolorsAuctionStorage],
) -> None:
    auction = await models.Auction.filter(
        id=withdraw.parameter.root,
    ).get()

    token = await auction.token

    token.holder = await auction.bidder
    await token.save()

    auction.status = models.AuctionStatus.FINISHED
    await auction.save()
