import demo_tezos_domains_big_map.models as models
from demo_tezos_domains_big_map.types.name_registry.big_map.store_expiry_map_key import StoreExpiryMapKey
from demo_tezos_domains_big_map.types.name_registry.big_map.store_expiry_map_value import StoreExpiryMapValue
from dipdup.context import HandlerContext
from dipdup.models import BigMapAction, BigMapDiff


async def on_update_expiry_map(
    ctx: HandlerContext,
    store_expiry_map: BigMapDiff[StoreExpiryMapKey, StoreExpiryMapValue],
) -> None:
    if store_expiry_map.action == BigMapAction.REMOVE:
        return
    assert store_expiry_map.value

    expiry = store_expiry_map.value.__root__
    record_name = bytes.fromhex(store_expiry_map.key.__root__).decode()
    await models.Expiry.update_or_create(
        id=record_name,
        defaults=dict(expiry=expiry),
    )
