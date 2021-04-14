from dipdup.models import HandlerContext, OperationContext

import demo_tezos_domains.models as models

from demo_tezos_domains.types.tld_registrar_buy.parameter.buy import Buy
from demo_tezos_domains.types.tld_registrar.parameter.execute import Execute as RegistrarExecute
from demo_tezos_domains.types.name_registry.parameter.execute import Execute as RegistryExecute


async def on_buy(
    ctx: HandlerContext,
    buy: OperationContext[Buy],
    registrar_execute: OperationContext[RegistrarExecute],
    registry_execute: OperationContext[RegistryExecute],
) -> None:
    print(registrar_execute.parameter)
    print(registrar_execute.storage)
    print(registry_execute.parameter)
    print(registry_execute.storage)
    quit()