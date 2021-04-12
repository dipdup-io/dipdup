from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.transfer_ownership import TransferOwnership


async def on_transfer_ownership(
    ctx: HandlerContext,
    transfer_ownership: OperationContext[TransferOwnership],
) -> None:
    ...
