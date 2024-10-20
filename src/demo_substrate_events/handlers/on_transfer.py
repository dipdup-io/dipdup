from demo_substrate_events import models as models
from demo_substrate_events.types.assethub.substrate_events.assets_transferred import AssetsTransferredPayload
from dipdup.context import HandlerContext
from dipdup.models.substrate import SubstrateEvent


async def on_transfer(
    ctx: HandlerContext,
    event: SubstrateEvent[AssetsTransferredPayload],
) -> None:
    amount = event.payload.get('amount') or event.payload['value']
    if not amount:
        return

    await ctx.execute_sql_query(
        'update_balance',
        event.payload['from'],
        '-' + amount,
        event.data.level,
    )

    await ctx.execute_sql_query(
        'update_balance',
        event.payload['to'],
        amount,
        event.data.level,
    )
