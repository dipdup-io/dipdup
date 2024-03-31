from demo_etherlink.types.ticketer.tezos_parameters.withdraw import WithdrawParameter
from demo_etherlink.types.ticketer.tezos_storage import TicketerStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TezosTzktOperationData
from dipdup.models.tezos_tzkt import TezosTzktSmartRollupExecute
from dipdup.models.tezos_tzkt import TezosTzktTransaction


async def on_withdraw(
    ctx: HandlerContext,
    sr_execute_0: TezosTzktSmartRollupExecute,
    withdraw: TezosTzktTransaction[WithdrawParameter, TicketerStorage],
    transaction_2: TezosTzktOperationData,
) -> None:
    ...