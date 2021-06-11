from typing import cast

from demo_registrydao.types.registry.storage import RegistryStorage
from dipdup.context import BigMapHandlerContext, HandlerContext, OperationHandlerContext
from dipdup.models import BigMapData, BigMapDiff, OperationData, Origination, Transaction


async def on_factory_origination(
    ctx: OperationHandlerContext,
    registry_origination: Origination[RegistryStorage],
) -> None:
    originated_contract = cast(str, registry_origination.data.originated_contract_address)
    index_name = f'registry_dao_{originated_contract}'
    if index_name not in ctx.config.indexes:
        ctx.add_contract(
            name=originated_contract,
            address=originated_contract,
            typename='registry',
        )
        ctx.add_index(
            name=index_name,
            template='registry_dao',
            values=dict(contract=originated_contract),
        )
        ctx.commit()
