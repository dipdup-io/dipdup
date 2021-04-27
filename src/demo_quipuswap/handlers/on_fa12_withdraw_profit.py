from decimal import Decimal

import demo_quipuswap.models as models
from demo_quipuswap.types.quipu_fa12.parameter.withdraw_profit import WithdrawProfit as WithdrawProfitParameter
from demo_quipuswap.types.quipu_fa12.storage import Storage as QuipuFa12Storage
from dipdup.models import OperationHandlerContext, OperationContext


async def on_fa12_withdraw_profit(
    ctx: OperationHandlerContext,
    withdraw_profit: OperationContext[WithdrawProfitParameter, QuipuFa12Storage],
) -> None:

    if ctx.template_values is None:
        raise Exception('This index must be templated')

    symbol = ctx.template_values['symbol']
    trader = withdraw_profit.data.sender_address

    position, _ = await models.Position.get_or_create(trader=trader, symbol=symbol)
    transaction = next(op for op in ctx.operations if op.amount)

    position.realized_pl += Decimal(transaction.amount) / (10 ** 6)  # type: ignore

    await position.save()
