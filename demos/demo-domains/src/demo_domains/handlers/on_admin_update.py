from dipdup.context import HandlerContext
from dipdup.models import Transaction

from demo_domains.types.name_registry.parameter.admin_update import AdminUpdateParameter
from demo_domains.types.name_registry.storage import NameRegistryStorage


async def on_admin_update(
    ctx: HandlerContext,
    admin_update: Transaction[AdminUpdateParameter, NameRegistryStorage],
) -> None:
    ...
