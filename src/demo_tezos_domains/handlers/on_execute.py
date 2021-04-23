from typing import cast
from dipdup.models import HandlerContext, OperationContext

import demo_tezos_domains.models as models

from demo_tezos_domains.types.name_registry.storage import Storage as NameRegistryStorage
from demo_tezos_domains.types.name_registry.parameter.execute import Execute


async def on_execute(
    ctx: HandlerContext,
    execute: OperationContext[Execute],
) -> None:
    storage = cast(NameRegistryStorage, execute.storage)  # FIXME: remove

    for name, item in storage.store.records.items():
        record_name = bytes.fromhex(name).decode()
        domain_name = bytes.fromhex(item.expiry_key).decode()

        if item.level == 2:
            assert domain_name == record_name
            expiration_dt = storage.store.expiry_map[name]
            domain = models.Domain(
                name=domain_name,
                owner=item.owner,
                expiry=expiration_dt,
                token_id=item.tzip12_token_id
            )
            await domain.save()

        record = models.Record(
            name=record_name,
            domain=domain_name,
            address=item.address
        )
        await record.save()
