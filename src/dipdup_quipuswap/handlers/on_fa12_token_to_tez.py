from typing import Dict, List, Optional

from dipdup.models import HandlerContext, OperationData
from dipdup_quipuswap.models import *
from dipdup_quipuswap.types.KT1CiSKXR68qYSxnbzjwvfeMCRburaSDonT2.parameter.tokenToTezPayment import Tokentotezpayment
from dipdup_quipuswap.types.KT1K9gCRgaLRFKTErYt1wVxA3Frb9FjasjTV.parameter.transfer import Transfer


async def on_fa12_token_to_tez(
    tokenToTezPayment: HandlerContext[Tokentotezpayment],
    transfer: HandlerContext[Transfer],
    operations: List[OperationData],
    template_values: Optional[Dict[str, str]] = None,
) -> None:
    ...
