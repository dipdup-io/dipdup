import demo_tezos_domains.models as models
from demo_tezos_domains.types.name_registry.parameter.admin_update import AdminUpdate
from dipdup.models import HandlerContext, OperationContext


async def on_admin_update(
    ctx: HandlerContext,
    admin_update: OperationContext[AdminUpdate],
) -> None:
    assert admin_update.storage
    if admin_update.storage.store.records:
        label = list(admin_update.storage.store.records.keys())[0]
        record = admin_update.storage.store.records[label]
        address = None
        if record.address:
            address, _ = await models.Address.get_or_create(address=record.address)
        owner, _ = await models.Address.get_or_create(address=record.owner)
        qualname = bytearray.fromhex(label).decode()
        name = qualname.split('.')[0]
        domain = models.Domain(
            label=label,
            name=name,
            qualname=qualname,
            address=address,
            owner=owner,
            parent=None,
            expires_at=None,
            token=None,
        )
        await domain.save()
    elif admin_update.storage.store.expiry_map:
        label, expires_at = list(admin_update.storage.store.expiry_map.items())[0]
        domain = await models.Domain.filter(label=label).get()
        domain.expires_at = expires_at
        await domain.save()
