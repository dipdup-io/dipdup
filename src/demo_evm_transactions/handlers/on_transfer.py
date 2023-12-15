from demo_evm_transactions import models as models
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidTransaction


async def on_transfer(
    ctx: HandlerContext,
    transaction: SubsquidTransaction,
) -> None:
    ...