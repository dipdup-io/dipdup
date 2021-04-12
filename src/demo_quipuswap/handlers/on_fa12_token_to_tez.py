from demo_quipuswap.models import *
from demo_quipuswap.types.fa12_token.parameter.transfer import Transfer
from demo_quipuswap.types.quipu_fa12.parameter.token_to_tez_payment import TokenToTezPayment
from dipdup.models import HandlerContext, OperationContext


async def on_fa12_token_to_tez(
    ctx: HandlerContext,
    token_to_tez_payment: OperationContext[TokenToTezPayment],
    transfer: OperationContext[Transfer],
) -> None:
    ...
