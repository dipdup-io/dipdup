from dipdup.context import HandlerContext
from dipdup.models.evm_node import EvmNodeTransactionData
from dipdup.models.evm_subsquid import SubsquidTransactionData

from kakarot import models as models


async def on_output_transaction(
    ctx: HandlerContext,
    transaction: SubsquidTransactionData | EvmNodeTransactionData,
) -> None:
    await models.Transaction(
        hash=transaction.hash,
        block_number=transaction.block_number,
        from_=transaction.from_,
        to=transaction.to,
    ).save()
