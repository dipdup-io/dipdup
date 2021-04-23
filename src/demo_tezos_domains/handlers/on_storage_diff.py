import logging
from typing import cast
from dipdup.models import HandlerContext, OperationContext

import demo_tezos_domains.models as models

from demo_tezos_domains.types.name_registry.storage import Storage as NameRegistryStorage

_logger = logging.getLogger(__name__)


async def on_storage_diff(storage: NameRegistryStorage) -> None:
    for name, item in storage.store.records.items():
        record_name = bytes.fromhex(name).decode()
        record_path = record_name.split('.')
        _logger.info(f'Processing `{record_name}`')

        if len(record_path) != int(item.level):
            _logger.error(f'Invalid record `{record_name}`: expected {item.level} chunks, got {len(record_path)}')
            return

        if item.level == "1":
            await models.TLD.update_or_create(
                id=record_name,
                defaults=dict(
                    owner=item.owner
                )
            )
        else:
            if item.level == "2":
                await models.Domain.update_or_create(
                    id=record_name,
                    defaults=dict(
                        tld_id=record_path[-1],
                        owner=item.owner,
                        expiry=storage.store.expiry_map.get(item.expiry_key),
                        token_id=int(item.tzip12_token_id) if item.tzip12_token_id else None
                    )
                )

            await models.Record.update_or_create(
                id=record_name,
                defaults=dict(
                    domain_id='.'.join(record_path[-2:]),
                    address=item.address
                )
            )
