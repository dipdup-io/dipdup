import demo_tezos_domains.models as models
from demo_tezos_domains.types.name_registry.parameter.execute import Execute
from demo_tezos_domains.types.name_registry_update_record.parameter.update_record import UpdateRecord
from dipdup.models import HandlerContext, OperationContext


async def on_update_record(
    ctx: HandlerContext,
    update_record: OperationContext[UpdateRecord],
    execute: OperationContext[Execute],
) -> None:
    label = update_record.parameter.name
    qualname = bytearray.fromhex(label).decode()

    domain = await models.Domain.filter(label=label).get_or_none()
    if domain:
        address, _ = await models.Address.get_or_create(address=update_record.parameter.address)
        owner, _ = await models.Address.get_or_create(address=update_record.parameter.owner)
        domain.address = address
        domain.owner = owner
        await domain.save()
    else:
        assert execute.storage
        label, record = list(execute.storage.store.records.items())[0]
        qualname = bytearray.fromhex(label).decode()
        name = qualname.split('.')[0]
        address = None
        if record.address:
            address, _ = await models.Address.get_or_create(address=record.address)
        owner, _ = await models.Address.get_or_create(address=record.owner)
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
