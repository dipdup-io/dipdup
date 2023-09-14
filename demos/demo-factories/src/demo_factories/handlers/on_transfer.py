import demo_factories.models as models
from demo_factories.types.token.parameter.transfer import TransferParameter
from demo_factories.types.token.storage import TokenStorage
from dipdup.context import HandlerContext
from dipdup.models import Transaction


async def on_transfer(
    ctx: HandlerContext,
    transfer: Transaction[TransferParameter, TokenStorage],
) -> None:
    for transfer_item in transfer.parameter.__root__:
        for tx in transfer_item.txs:
            await models.Transfer.create(
                from_=transfer_item.from_,
                to=tx.to_,
                amount=tx.amount,
            )
