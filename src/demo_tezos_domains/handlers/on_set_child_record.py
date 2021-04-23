from dipdup.models import HandlerContext, OperationContext

import demo_tezos_domains.models as models

from demo_tezos_domains.types.name_registry_set_child_record.parameter.set_child_record import SetChildRecord
from demo_tezos_domains.types.name_registry.parameter.execute import Execute


async def on_set_child_record(
    ctx: HandlerContext,
    set_child_record: OperationContext[SetChildRecord],
    execute: OperationContext[Execute],
) -> None:
    assert execute.storage
    parent_label = set_child_record.parameter.parent
    parent = await models.Domain.filter(label=parent_label).get()
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
        parent=parent,
        expires_at=None,
        token=None,
    )
    await domain.save()
