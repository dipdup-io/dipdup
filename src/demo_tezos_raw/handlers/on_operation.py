from demo_tezos_raw import models
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosOperationData


async def on_operation(
    ctx: HandlerContext,
    operation: TezosOperationData,
) -> None:
    await models.Operation.create(
        hash=operation.hash,
        level=operation.level,
        type=operation.type,
    )