from decimal import Decimal

import demo_dex.models as models
from demo_dex.types.fa2_token.parameter.transfer import TransferParameter
from demo_dex.types.fa2_token.storage import Fa2TokenStorage
from demo_dex.types.quipu_fa2.parameter.tez_to_token_payment import TezToTokenPaymentParameter
from demo_dex.types.quipu_fa2.storage import QuipuFa2Storage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktTransaction


async def on_fa2_tez_to_token(
    ctx: HandlerContext,
    tez_to_token_payment: TzktTransaction[TezToTokenPaymentParameter, QuipuFa2Storage],
    transfer: TzktTransaction[TransferParameter, Fa2TokenStorage],
) -> None:
    decimals = int(ctx.template_values['decimals'])
    symbol = ctx.template_values['symbol']
    trader = tez_to_token_payment.data.sender_address

    min_token_quantity = Decimal(tez_to_token_payment.parameter.min_out) / (10**decimals)
    assert tez_to_token_payment.data.amount is not None
    token_quantity = sum(Decimal(tx.amount) for tx in transfer.parameter.__root__[0].txs) / (10**decimals)
    tez_quantity = Decimal(tez_to_token_payment.data.amount) / (10**6)
    assert min_token_quantity <= token_quantity, tez_to_token_payment.data.hash

    trade = models.Trade(
        symbol=symbol,
        trader=trader,
        side=models.TradeSide.BUY,
        quantity=token_quantity,
        price=token_quantity / tez_quantity,
        slippage=1 - (min_token_quantity / token_quantity),
        level=transfer.data.level,
        timestamp=transfer.data.timestamp,
    )
    await trade.save()
