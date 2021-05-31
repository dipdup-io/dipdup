from typing import Optional

import demo_quipuswap.models as models
from demo_quipuswap.types.quipu_fa2.parameter.transfer import TransferParameter
from demo_quipuswap.types.quipu_fa2.storage import QuipuFa2Storage
from dipdup.models import OperationData, OperationHandlerContext, OriginationContext, TransactionContext


async def on_fa2_transfer(
    ctx: OperationHandlerContext,
    transfer: TransactionContext[TransferParameter, QuipuFa2Storage],
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    transfer_parameter = transfer.parameter.__root__[0]

    symbol = ctx.template_values['symbol']
    from_address = transfer_parameter.from_
    from_position, _ = await models.Position.get_or_create(trader=from_address, symbol=symbol)

    for transfer_tx in transfer_parameter.txs:
        to_address = transfer_tx.to_
        value = int(transfer_tx.amount)

        from_position.shares_qty -= value  # type: ignore
        assert from_position.shares_qty >= 0, transfer.data.hash

        to_position, _ = await models.Position.get_or_create(trader=to_address, symbol=symbol)
        to_position.shares_qty += value  # type: ignore
        assert to_position.shares_qty >= 0, transfer.data.hash
        await to_position.save()

    await from_position.save()
