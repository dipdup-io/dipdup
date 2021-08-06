from decimal import Decimal
from typing import Optional

import demo_quipuswap.models as models
from demo_quipuswap.types.quipu_fa2.parameter.withdraw_profit import WithdrawProfitParameter
from demo_quipuswap.types.quipu_fa2.storage import QuipuFa2Storage
from dipdup.context import HandlerContext
from dipdup.models import OperationData, Transaction


async def on_fa2_withdraw_profit(
    ctx: HandlerContext,
    withdraw_profit: Transaction[WithdrawProfitParameter, QuipuFa2Storage],
    transaction_0: Optional[OperationData] = None,
) -> None:
    symbol = ctx.template_values['symbol']
    trader = withdraw_profit.data.sender_address

    position, _ = await models.Position.get_or_create(trader=trader, symbol=symbol)

    if transaction_0:
        assert transaction_0.amount is not None
        position.realized_pl += Decimal(transaction_0.amount) / (10 ** 6)  # type: ignore

        await position.save()
