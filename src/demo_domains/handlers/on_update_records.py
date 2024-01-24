from contextlib import suppress
from typing import cast

import orjson
from demo_domains import models as models
from demo_domains.types.name_registry.tezos_big_maps.store_records_key import StoreRecordsKey
from demo_domains.types.name_registry.tezos_big_maps.store_records_value import StoreRecordsValue
from dipdup.context import HandlerContext
from dipdup.datasources.tezos_tzkt import TzktDatasource
from dipdup.models.tezos_tzkt import TzktBigMapDiff


def decode_domain_data(data: dict[str, str]) -> dict[str, str]:
    res = {}
    if isinstance(data, dict):
        for k, v in data.items():
            with suppress(ValueError, orjson.JSONDecodeError):
                res[k] = orjson.loads(bytes.fromhex(v).decode())
    return res


async def on_update_records(
    ctx: HandlerContext,
    store_records: TzktBigMapDiff[StoreRecordsKey, StoreRecordsValue],
) -> None:
    if not store_records.action.has_value:
        return
    assert store_records.key
    assert store_records.value

    record_name = bytes.fromhex(store_records.key.__root__).decode()
    record_path = record_name.split('.')
    domain_data = decode_domain_data(store_records.value.data)
    ctx.logger.info('Processing `%s`', record_name)

    if len(record_path) != int(store_records.value.level):
        ctx.logger.error(
            'Invalid record `%s`: expected %s chunks, got %s',
            record_name,
            store_records.value.level,
            len(record_path),
        )
        return

    if store_records.value.level == '1':
        await models.TLD.update_or_create(
            id=record_name,
            defaults={
                'owner': store_records.value.owner,
            },
        )
        return

    if store_records.value.level == '2':
        token_id = store_records.value.tzip12_token_id
        if token_id:
            await ctx.update_token_metadata(
                network=cast(TzktDatasource, ctx.datasource).name,
                address=store_records.data.contract_address,
                token_id=token_id,
                metadata={
                    'name': record_name,
                    'symbol': 'TD',
                    'decimals': '0',
                    'isBooleanAmount': True,
                    'domainData': domain_data,
                },
            )

        expiry = await models.Expiry.get_or_none(id=record_name)
        expires_at = expiry.expires_at if expiry else None

        await models.Domain.update_or_create(
            id=record_name,
            defaults={
                'tld_id': record_path[-1],
                'owner': store_records.value.owner,
                'token_id': token_id,
                'expires_at': expires_at,
            },
        )

    await models.Record.update_or_create(
        id=record_name,
        defaults={
            'domain_id': '.'.join(record_path[-2:]),
            'address': store_records.value.address,
            'expired': False,
            'metadata': domain_data,
        },
    )

    if store_records.value.address is not None:
        await ctx.update_contract_metadata(
            network=cast(TzktDatasource, ctx.datasource).name,
            address=store_records.value.address,
            metadata={**domain_data, 'name': record_name},
        )