import demo_tezos_domains_big_map.models as models
from demo_tezos_domains_big_map.types.name_registry.big_map.store_records_key import StoreRecordsKey
from demo_tezos_domains_big_map.types.name_registry.big_map.store_records_value import StoreRecordsValue
from dipdup.context import HandlerContext
from dipdup.models import BigMapAction, BigMapDiff


async def on_update_records(
    ctx: HandlerContext,
    store_records: BigMapDiff[StoreRecordsKey, StoreRecordsValue],
) -> None:
    if store_records.action == BigMapAction.REMOVE:
        return
    assert store_records.value

    record_name = bytes.fromhex(store_records.key.__root__).decode()
    record_path = record_name.split('.')
    ctx.logger.info('Processing `%s`', record_name)

    if len(record_path) != int(store_records.value.level):
        ctx.logger.error('Invalid record `%s`: expected %s chunks, got %s', record_name, store_records.value.level, len(record_path))
        return

    if store_records.value.level == "1":
        await models.TLD.update_or_create(id=record_name, defaults=dict(owner=store_records.value.owner))
    else:
        if store_records.value.level == "2":
            await models.Domain.update_or_create(
                id=record_name,
                defaults=dict(
                    tld_id=record_path[-1],
                    owner=store_records.value.owner,
                    token_id=int(store_records.value.tzip12_token_id) if store_records.value.tzip12_token_id else None,
                ),
            )

        await models.Record.update_or_create(
            id=record_name,
            defaults=dict(domain_id='.'.join(record_path[-2:]), address=store_records.value.address),
        )
