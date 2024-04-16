from decimal import Decimal

import demo_dex.models as models
from demo_dex.types.quipu_fa2.tezos_parameters.withdraw_profit import WithdrawProfitParameter
from demo_dex.types.quipu_fa2.tezos_storage import QuipuFa2Storage
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosTzktOperationData
from dipdup.models.tezos import TezosTzktTransaction


async def on_fa2_withdraw_profit(
    ctx: HandlerContext,
    withdraw_profit: TezosTzktTransaction[WithdrawProfitParameter, QuipuFa2Storage],
    transaction_0: TezosTzktOperationData | None = None,
) -> None:
    symbol = ctx.template_values['symbol']
    trader = withdraw_profit.data.sender_address

    position, _ = await models.Position.get_or_create(trader=trader, symbol=symbol)

    if transaction_0:
        assert transaction_0.amount is not None
        position.realized_pl += Decimal(transaction_0.amount) / (10**6)

        await position.save()