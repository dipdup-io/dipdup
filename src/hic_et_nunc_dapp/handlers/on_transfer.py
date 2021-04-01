from hic_et_nunc_dapp.models import *
from hic_et_nunc_dapp.types.KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton.parameter.transfer import Transfer
from pytezos_dapps.models import HandlerContext


async def on_transfer(
    transfer: HandlerContext[Transfer],
) -> None:
    ...
