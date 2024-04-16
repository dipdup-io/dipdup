from demo_raw import models
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosTzktOperationData


async def on_operation(
    ctx: HandlerContext,
    operation: TezosTzktOperationData,
) -> None:
    await models.Operation.create(
        hash=operation.hash,
        level=operation.level,
        type=operation.type,
    )