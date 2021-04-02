from dipdup_hic_et_nunc.models import *
from dipdup_hic_et_nunc.types.KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton.parameter.transfer import Transfer

from dipdup.models import HandlerContext


async def on_transfer(
    transfer: HandlerContext[Transfer],
) -> None:
    ...
