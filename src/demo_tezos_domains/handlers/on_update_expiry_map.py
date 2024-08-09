from datetime import datetime
from typing import Any
from typing import cast

import strict_rfc3339  # type: ignore[import-untyped]
from demo_tezos_domains import models as models
from demo_tezos_domains.types.name_registry.tezos_big_maps.store_expiry_map_key import StoreExpiryMapKey
from demo_tezos_domains.types.name_registry.tezos_big_maps.store_expiry_map_value import StoreExpiryMapValue
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosBigMapDiff


async def on_update_expiry_map(
    ctx: HandlerContext,
    store_expiry_map: TezosBigMapDiff[StoreExpiryMapKey, StoreExpiryMapValue],
) -> None:
    if not store_expiry_map.action.has_value:
        return
    assert store_expiry_map.key
    assert store_expiry_map.value

    expires_at = datetime.utcfromtimestamp(strict_rfc3339.rfc3339_to_timestamp(store_expiry_map.value.root))
    record_name = bytes.fromhex(store_expiry_map.key.root).decode()
    await models.Expiry.update_or_create(
        id=record_name,
        defaults={'expires_at': expires_at},
    )

    domain = await models.Domain.get_or_none(id=record_name).prefetch_related('records')
    if domain is None:
        return

    domain.expires_at = expires_at
    await domain.save()

    if expires_at < datetime.utcnow():
        return

    ctx.logger.debug('Updating expiration status for all records associated with domain %s (renewal)', domain.id)
    for record in domain.records:
        record.expired = False
        await record.save()
        if record.address is not None:
            metadata = {} if record.metadata is None else cast(dict[str, Any], record.metadata)
            metadata.update(name=record.id)
            await ctx.update_contract_metadata(
                network=ctx.handler_config.parent.datasources[0].name,
                address=record.address,
                metadata=metadata,
            )
