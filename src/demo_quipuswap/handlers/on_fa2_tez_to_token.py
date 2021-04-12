from demo_quipuswap.models import *
from demo_quipuswap.types.fa2_token.parameter.transfer import Transfer
from demo_quipuswap.types.quipu_fa2.parameter.tez_to_token_payment import TezToTokenPayment
from dipdup.models import HandlerContext, OperationContext


async def on_fa2_tez_to_token(
    ctx: HandlerContext,
    tez_to_token_payment: OperationContext[TezToTokenPayment],
    transfer: OperationContext[Transfer],
) -> None:
    ...
