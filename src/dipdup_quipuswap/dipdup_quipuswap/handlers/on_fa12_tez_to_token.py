from dipdup.models import HandlerContext, OperationContext

from dipdup_quipuswap.models import *


from dipdup_quipuswap.types.fa12_dex.parameter.tezToTokenPayment import TezToTokenPayment
from dipdup_quipuswap.types.fa12_token.parameter.transfer import Transfer

async def on_fa12_tez_to_token(
    ctx: HandlerContext,
    tezToTokenPayment: OperationContext[TezToTokenPayment],
    transfer: OperationContext[Transfer],
) -> None:
    ...