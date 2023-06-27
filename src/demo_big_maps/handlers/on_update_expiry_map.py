import demo_big_maps.models as models
from demo_big_maps.types.name_registry.tezos_big_maps.store_expiry_map_key import StoreExpiryMapKey
from demo_big_maps.types.name_registry.tezos_big_maps.store_expiry_map_value import StoreExpiryMapValue
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktBigMapDiff


async def on_update_expiry_map(
    ctx: HandlerContext,
    store_expiry_map: TzktBigMapDiff[StoreExpiryMapKey, StoreExpiryMapValue],
) -> None:
    if not store_expiry_map.action.has_value:
        return
    assert store_expiry_map.key
    assert store_expiry_map.value

    timestamp = store_expiry_map.value.__root__
    record_name = bytes.fromhex(store_expiry_map.key.__root__).decode()
    await models.Expiry.update_or_create(
        id=record_name,
        defaults={'timestamp': timestamp},
    )