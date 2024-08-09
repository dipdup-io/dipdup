import demo_tezos_factories.models as models
from demo_tezos_factories.types.token.tezos_parameters.transfer import TransferParameter
from demo_tezos_factories.types.token.tezos_storage import TokenStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosTransaction


async def on_transfer(
    ctx: HandlerContext,
    transfer: TezosTransaction[TransferParameter, TokenStorage],
) -> None:
    for transfer_item in transfer.parameter.root:
        for tx in transfer_item.txs:
            await models.Transfer.create(
                from_=transfer_item.from_,
                to=tx.to_,
                amount=tx.amount,
            )
