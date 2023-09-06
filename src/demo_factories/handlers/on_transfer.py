from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktTransaction

import demo_factories.models as models
from demo_factories.types.token.tezos_parameters.transfer import TransferParameter
from demo_factories.types.token.tezos_storage import TokenStorage


async def on_transfer(
    ctx: HandlerContext,
    transfer: TzktTransaction[TransferParameter, TokenStorage],
) -> None:
    transfers = []
    for transfer_item in transfer.parameter.__root__:
        transfers.append(models.Transfer(
            from_=transfer_item.from_,
            to_=[models.Tx(to_=tx.to_, amount=tx.amount) for tx in transfer_item.txs]
        ))
    await models.Transfer.bulk_create(transfers)