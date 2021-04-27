import demo_tezos_domains_big_map.models as models
from demo_tezos_domains_big_map.types.name_registry.big_map.store_records_key import StoreRecordsKey
from demo_tezos_domains_big_map.types.name_registry.big_map.store_records_value import StoreRecordsValue
from dipdup.models import BigMapContext, BigMapHandlerContext


async def on_update(
    ctx: BigMapHandlerContext,
    store_records: BigMapContext[StoreRecordsKey, StoreRecordsValue],
) -> None:
    ...
