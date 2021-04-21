import demo_tezos_domains.models as models
from demo_tezos_domains.types.name_registry.parameter.execute import Execute as RegistryExecute
from demo_tezos_domains.types.tld_registrar.parameter.execute import Execute as RegistrarExecute
from demo_tezos_domains.types.tld_registrar_buy.parameter.buy import Buy
from dipdup.models import HandlerContext, OperationContext


async def on_buy(
    ctx: HandlerContext,
    buy: OperationContext[Buy],
    registrar_execute: OperationContext[RegistrarExecute],
    registry_execute: OperationContext[RegistryExecute],
) -> None:
    assert registry_execute.storage is not None
    owner, _ = await models.Address.get_or_create(address=buy.data.sender_address)
    if buy.parameter.address:
        address, _ = await models.Address.get_or_create(address=buy.parameter.address)
    else:
        address = None  # type: ignore

    name = bytearray.fromhex(buy.parameter.label).decode()
    record = dir(registry_execute.storage.store.records)[0]
    qualname = bytearray.fromhex(record).decode()
    expires_at = getattr(registry_execute.storage.store.expiry_map, record)
    token = dir(registry_execute.storage.store.tzip12_tokens)[0]
    domain = models.Domain(
        label=buy.parameter.label,
        name=name,
        qualname=qualname,
        address=address,
        owner=owner,
        parent=None,
        expires_at=expires_at,
        token=token,
    )
    await domain.save()
