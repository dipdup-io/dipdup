from typing import Optional

import demo_dex.models as models
from demo_dex.types.quipuswap_fa2.parameter.transfer import TransferParameter
from demo_dex.types.quipuswap_fa2.storage import QuipuswapFa2Storage
from dipdup.models import OperationData, OperationHandlerContext, OriginationContext, TransactionContext


async def on_fa2_transfer(
    ctx: OperationHandlerContext,
    transfer: TransactionContext[TransferParameter, QuipuswapFa2Storage],
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    transfer_parameter = transfer.parameter.__root__[0]

    symbol, _ = await models.Symbol.get_or_create(symbol=ctx.template_values['symbol'])
    from_trader, _ = await models.Trader.get_or_create(address=transfer_parameter.from_)
    from_position, _ = await models.Position.get_or_create(trader=from_trader, symbol=symbol)

    for transfer_tx in transfer_parameter.txs:
        to_trader, _ = await models.Trader.get_or_create(address=transfer_tx.to_)

        value = int(transfer_tx.amount)

        from_position.shares_qty -= value  # type: ignore
        assert from_position.shares_qty >= 0, transfer.data.hash

        to_position, _ = await models.Position.get_or_create(trader=to_trader, symbol=symbol)
        to_position.shares_qty += value  # type: ignore
        assert to_position.shares_qty >= 0, transfer.data.hash
        await to_position.save()

    await from_position.save()
