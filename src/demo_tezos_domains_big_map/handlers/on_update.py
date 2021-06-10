import logging
from typing import List, Optional

import demo_tezos_domains_big_map.models as models
from demo_tezos_domains_big_map.types.name_registry.big_map.store_expiry_map_key import StoreExpiryMapKey
from demo_tezos_domains_big_map.types.name_registry.big_map.store_expiry_map_value import StoreExpiryMapValue
from demo_tezos_domains_big_map.types.name_registry.big_map.store_records_key import StoreRecordsKey
from demo_tezos_domains_big_map.types.name_registry.big_map.store_records_value import StoreRecordsValue
from dipdup.models import BigMapAction, BigMapDiff, BigMapHandlerContext

_logger = logging.getLogger(__name__)


async def on_update(
    ctx: BigMapHandlerContext,
    store_records: List[BigMapDiff[StoreRecordsKey, StoreRecordsValue]],
    store_expiry_map: List[BigMapDiff[StoreExpiryMapKey, StoreExpiryMapValue]],
) -> None:
    for diff in store_records:
        if diff.action in (BigMapAction.ADD, BigMapAction.UPDATE):
            assert diff.value
            record_name = bytes.fromhex(diff.key.__root__).decode()
            record_path = record_name.split('.')
            _logger.info('Processing `%s`', record_name)

            if len(record_path) != int(diff.value.level):
                _logger.error('Invalid record `%s`: expected %s chunks, got %s', record_name, diff.value.level, len(record_path))
                return

            if diff.value.level == "1":
                await models.TLD.update_or_create(id=record_name, defaults=dict(owner=diff.value.owner))
            else:
                if diff.value.level == "2":
                    expiry: Optional[str]
                    if store_expiry_map:
                        assert store_expiry_map[0].value
                        expiry = store_expiry_map[0].value.__root__
                    else:
                        expiry = None
                    await models.Domain.update_or_create(
                        id=record_name,
                        defaults=dict(
                            tld_id=record_path[-1],
                            owner=diff.value.owner,
                            expiry=expiry,
                            token_id=int(diff.value.tzip12_token_id) if diff.value.tzip12_token_id else None,
                        ),
                    )

                await models.Record.update_or_create(
                    id=record_name,
                    defaults=dict(domain_id='.'.join(record_path[-2:]), address=diff.value.address),
                )
