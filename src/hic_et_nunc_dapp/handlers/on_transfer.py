import logging

from hic_et_nunc_dapp.types.KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton.parameter.transfer import Transfer
from pytezos_dapps.models import HandlerContext

logger = logging.getLogger(__name__)


async def on_transfer(transfer: HandlerContext[Transfer]):
    for item in transfer.parameter:
        sub_item = item[1][0]
        for tx in sub_item.txs:
            print(tx)
