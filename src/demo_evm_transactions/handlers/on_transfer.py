from demo_evm_transactions import models as models
from demo_evm_transactions.types.eth_usdt.evm_methods.transfer import Transfer
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidTransaction


async def on_transfer(
    ctx: HandlerContext,
    transaction: SubsquidTransaction[Transfer],
) -> None:
    ...