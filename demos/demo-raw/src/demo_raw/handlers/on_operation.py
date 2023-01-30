from demo_raw import models
from dipdup.context import HandlerContext
from dipdup.models.tzkt import OperationData


async def on_operation(
    ctx: HandlerContext,
    operation: OperationData,
) -> None:
    await models.Operation.create(
        hash=operation.hash,
        level=operation.level,
        type=operation.type,
    )
