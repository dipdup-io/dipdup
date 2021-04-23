from decimal import Decimal

import demo_quipuswap.models as models
from demo_quipuswap.types.fa2_token.parameter.transfer import Transfer
from demo_quipuswap.types.quipu_fa2.parameter.divest_liquidity import DivestLiquidity
from dipdup.models import HandlerContext, OperationContext


async def on_fa20_divest_liquidity(
    ctx: HandlerContext,
    divest_liquidity: OperationContext[DivestLiquidity],
    transfer: OperationContext[Transfer],
) -> None:

    if ctx.template_values is None:
        raise Exception('This index must be templated')

    decimals = int(ctx.template_values['decimals'])
    trader, _ = await models.Trader.get_or_create(address=divest_liquidity.data.sender_address)
    instrument, _ = await models.Instrument.get_or_create(symbol=ctx.template_values['symbol'])
    position, _ = await models.Position.get_or_create(trader=trader, instrument=instrument)

    transaction = next(op for op in ctx.operations if op.amount)
    position.tez_qty -= Decimal(transaction.amount) / (10 ** 6)  # type: ignore
    position.token_qty -= Decimal(transfer.parameter.__root__[0].txs[0].amount) / (10 ** decimals)
    await position.save()
