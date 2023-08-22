import demo_factories.models as models
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktTransaction


async def on_transfer(
    ctx: HandlerContext,
    transfer: TzktTransaction,
) -> None:
    transfers = []
    for transfer in TzktTransaction.parameter:
        transfers.append(models.Transfer(
            from_=TzktTransaction.parameter.from_,
            to=[models.Tx(to_=tx.to_, amount=tx.amount) for tx in transfer.txs]
        ))
    await models.Transfer.bulk_create(transfers)