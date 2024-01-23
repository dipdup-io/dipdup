from demo_etherlink.types.ticketer.tezos_parameters.withdraw import WithdrawParameter
from demo_etherlink.types.ticketer.tezos_storage import TicketerStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktOperationData
from dipdup.models.tezos_tzkt import TzktSmartRollupExecute
from dipdup.models.tezos_tzkt import TzktTransaction


async def on_withdraw(
    ctx: HandlerContext,
    sr_execute_0: TzktSmartRollupExecute,
    withdraw: TzktTransaction[WithdrawParameter, TicketerStorage],
    transaction_2: TzktOperationData,
) -> None:
    ...