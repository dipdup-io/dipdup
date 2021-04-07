from typing import Dict, List, Optional
from dipdup.models import HandlerContext, OperationData

from dipdup_hic_et_nunc.models import *

from dipdup_hic_et_nunc.types.KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9.parameter.mint_OBJKT import MintObjkt
from dipdup_hic_et_nunc.types.KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton.parameter.mint import Mint

async def on_mint(
    mint_OBJKT: HandlerContext[MintObjkt],
    mint: HandlerContext[Mint],
    operations: List[OperationData],
    template_values: Optional[Dict[str, str]] = None,
) -> None:
    ...