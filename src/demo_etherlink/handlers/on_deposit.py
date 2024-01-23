from demo_etherlink.types.rollup.tezos_parameters.default import DefaultParameter as RollupDefaultParameter
from demo_etherlink.types.rollup.tezos_storage import RollupStorage
from demo_etherlink.types.ticket_helper.tezos_parameters.default import DefaultParameter
from demo_etherlink.types.ticket_helper.tezos_storage import TicketHelperStorage
from demo_etherlink.types.ticketer.tezos_parameters.deposit import DepositParameter
from demo_etherlink.types.ticketer.tezos_storage import TicketerStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktTransaction


async def on_deposit(
    ctx: HandlerContext,
    deposit: TzktTransaction[DepositParameter, TicketerStorage],
    default: TzktTransaction[DefaultParameter, TicketHelperStorage],
    rollup_default: TzktTransaction[RollupDefaultParameter, RollupStorage],
) -> None:
    ...