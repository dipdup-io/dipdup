from demo_etherlink import models as models
from demo_etherlink.types.ticketer.tezos_parameters.withdraw import WithdrawParameter
from demo_etherlink.types.ticketer.tezos_storage import TicketerStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TezosTzktOperationData as OperationData
from dipdup.models.tezos_tzkt import TezosTzktSmartRollupExecute as SmartRollupExecute
from dipdup.models.tezos_tzkt import TezosTzktTransaction as Transaction


async def on_withdraw(
    ctx: HandlerContext,
    sr_execute_0: SmartRollupExecute,
    withdraw: Transaction[WithdrawParameter, TicketerStorage],
    transaction_2: OperationData,
) -> None:
    ...