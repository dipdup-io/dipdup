from typing import Dict, List, Optional
from dipdup.models import HandlerContext, OperationData

from dipdup_quipuswap.models import *

from dipdup_quipuswap.types.KT1V41fGzkdTJki4d11T1Rp9yPkCmDhB7jph.parameter.tokenToTezPayment import Tokentotezpayment
from dipdup_quipuswap.types.KT1AFA2mwNUMNd4SsujE1YYp29vd8BZejyKW.parameter.transfer import Transfer

async def on_fa2_token_to_tez(
    tokenToTezPayment: HandlerContext[Tokentotezpayment],
    transfer: HandlerContext[Transfer],
    operations: List[OperationData],
    template_values: Optional[Dict[str, str]] = None,
) -> None:
    ...