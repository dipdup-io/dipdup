from decimal import Decimal
from typing import Optional

import demo_dex.models as models
from demo_dex.types.quipuswap_fa12.parameter.withdraw_profit import WithdrawProfitParameter
from demo_dex.types.quipuswap_fa12.storage import QuipuswapFa12Storage
from dipdup.models import OperationData, OperationHandlerContext, OriginationContext, TransactionContext


async def on_fa12_withdraw_profit(
    ctx: OperationHandlerContext,
    withdraw_profit: TransactionContext[WithdrawProfitParameter, QuipuswapFa12Storage],
    transaction_0: Optional[OperationData] = None,
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    symbol, _ = await models.Symbol.get_or_create(symbol=ctx.template_values['symbol'])
    trader, _ = await models.Trader.get_or_create(address=withdraw_profit.data.sender_address)

    position, _ = await models.Position.get_or_create(trader=trader, symbol=symbol)
    if transaction_0:
        assert transaction_0.amount is not None
        position.realized_pl += Decimal(transaction_0.amount) / (10 ** 6)  # type: ignore

        await position.save()
