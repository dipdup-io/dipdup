from demo_etherlink import models as models
from demo_etherlink.types.rollup.tezos_parameters.default import DefaultParameter as RollupDefaultParameter
from demo_etherlink.types.rollup.tezos_storage import RollupStorage
from demo_etherlink.types.ticket_helper.tezos_parameters.default import DefaultParameter
from demo_etherlink.types.ticket_helper.tezos_storage import TicketHelperStorage
from demo_etherlink.types.ticketer.tezos_parameters.deposit import DepositParameter
from demo_etherlink.types.ticketer.tezos_storage import TicketerStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TezosTzktTransaction as Transaction


async def on_deposit(
    ctx: HandlerContext,
    deposit: Transaction[DepositParameter, TicketerStorage],
    default: Transaction[DefaultParameter, TicketHelperStorage],
    rollup_default: Transaction[RollupDefaultParameter, RollupStorage],
) -> None:
    ...