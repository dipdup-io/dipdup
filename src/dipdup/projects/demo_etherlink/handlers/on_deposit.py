from demo_etherlink.types.controller.tezos_parameters.deposit import DepositParameter
from demo_etherlink.types.controller.tezos_storage import ControllerStorage
from demo_etherlink.types.rollup.tezos_parameters.default import DefaultParameter
from demo_etherlink.types.rollup.tezos_storage import RollupStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktTransaction


async def on_deposit(
    ctx: HandlerContext,
    deposit: TzktTransaction[DepositParameter, ControllerStorage],
    default: TzktTransaction[DefaultParameter, RollupStorage],
) -> None:
    raise Exception("🥳 it's a match!")