from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.confirm_migration import ConfirmMigration


async def on_confirm_migration(
    ctx: HandlerContext,
    confirm_migration: OperationContext[ConfirmMigration],
) -> None:
    ...
