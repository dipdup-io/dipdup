from typing import Optional, cast

import demo_registrydao.models as models
from demo_registrydao.types.registry.storage import RegistryStorage
from dipdup.config import ContractConfig, StaticTemplateConfig
from dipdup.models import OperationData, OperationHandlerContext, OriginationContext, TransactionContext


async def on_factory_origination(
    ctx: OperationHandlerContext,
    registry_origination: OriginationContext[RegistryStorage],
) -> None:
    originated_contract = cast(str, registry_origination.data.originated_contract_address)
    index_name = f'registry_dao_{originated_contract}'
    if index_name not in ctx.config.indexes:
        ctx.config.contracts[originated_contract] = ContractConfig(
            address=originated_contract,
            typename='registry',
        )
        ctx.config.indexes[index_name] = StaticTemplateConfig(
            template='registry_dao',
            values=dict(contract=originated_contract),
        )
        ctx.commit()
