from demo_tezos_etherlink import models as models
from demo_tezos_etherlink.types.rollup.tezos_parameters.default import DefaultParameter as RollupDefaultParameter
from demo_tezos_etherlink.types.rollup.tezos_storage import RollupStorage
from demo_tezos_etherlink.types.ticket_helper.tezos_parameters.default import DefaultParameter
from demo_tezos_etherlink.types.ticket_helper.tezos_storage import TicketHelperStorage
from demo_tezos_etherlink.types.ticketer.tezos_parameters.deposit import DepositParameter
from demo_tezos_etherlink.types.ticketer.tezos_storage import TicketerStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosTransaction


async def on_deposit(
    ctx: HandlerContext,
    deposit: TezosTransaction[DepositParameter, TicketerStorage],
    default: TezosTransaction[DefaultParameter, TicketHelperStorage],
    rollup_default: TezosTransaction[RollupDefaultParameter, RollupStorage],
) -> None: ...
