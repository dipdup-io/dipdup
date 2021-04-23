import json
from dipdup.models import HandlerContext, OperationContext

import demo_tezos_domains.models as models

from demo_tezos_domains.types.name_registry.parameter.execute import Execute


async def on_execute(
    ctx: HandlerContext,
    execute: OperationContext[Execute],
) -> None:
    for key in execute.storage.store.records:
        if '686f6d65626173652e74657a' in key:
            print(execute.data.hash)
