from typing import cast

from dipdup.context import HandlerContext
from dipdup.models import OperationData


async def on_factory_origination(
    ctx: HandlerContext,
    origination_0: OperationData,
) -> None:
    originated_contract = cast(str, origination_0.originated_contract_address)
    name = f'dex_{originated_contract}'
    await ctx.add_contract(
        name=originated_contract,
        address=originated_contract,
        typename='dex',
    )
    await ctx.add_index(
        name=name,
        template='dex',
        values={'contract': originated_contract},
    )
