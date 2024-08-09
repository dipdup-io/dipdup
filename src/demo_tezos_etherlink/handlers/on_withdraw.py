from demo_tezos_etherlink import models as models
from demo_tezos_etherlink.types.ticketer.tezos_parameters.withdraw import WithdrawParameter
from demo_tezos_etherlink.types.ticketer.tezos_storage import TicketerStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosOperationData
from dipdup.models.tezos import TezosSmartRollupExecute
from dipdup.models.tezos import TezosTransaction


async def on_withdraw(
    ctx: HandlerContext,
    sr_execute_0: TezosSmartRollupExecute,
    withdraw: TezosTransaction[WithdrawParameter, TicketerStorage],
    transaction_2: TezosOperationData,
) -> None: ...
