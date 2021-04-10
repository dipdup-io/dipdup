from dipdup.models import HandlerContext, OperationContext

from dipdup_quipuswap.models import *


from dipdup_quipuswap.types.fa12_dex.parameter.tokenToTezPayment import TokenToTezPayment
from dipdup_quipuswap.types.fa12_token.parameter.transfer import Transfer

async def on_fa12_token_to_tez(
    ctx: HandlerContext,
    tokenToTezPayment: OperationContext[TokenToTezPayment],
    transfer: OperationContext[Transfer],
) -> None:
    ...