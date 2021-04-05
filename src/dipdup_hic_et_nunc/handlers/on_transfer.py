from typing import List
from dipdup.models import HandlerContext, OperationData

from dipdup_hic_et_nunc.models import *

from dipdup_hic_et_nunc.types.KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton.parameter.transfer import Transfer

async def on_transfer(
    transfer: HandlerContext[Transfer],
    operations: List[OperationData],
) -> None:
    ...