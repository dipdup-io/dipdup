from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosHeadBlockData
from reorg.models import Cursor


async def on_head(
    ctx: HandlerContext,
    head: TezosHeadBlockData,
) -> None:
    cursor_id = head.level
    await Cursor.filter(level=0, id__lt=cursor_id).delete()
    await Cursor.create(id=cursor_id, level=0, index=0)
