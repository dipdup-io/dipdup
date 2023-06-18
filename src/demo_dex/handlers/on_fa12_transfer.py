import demo_dex.models as models
from demo_dex.types.quipu_fa12.tezos_parameters.transfer import TransferParameter
from demo_dex.types.quipu_fa12.tezos_storage import QuipuFa12Storage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktTransaction


async def on_fa12_transfer(
    ctx: HandlerContext,
    transfer: TzktTransaction[TransferParameter, QuipuFa12Storage],
) -> None:
    symbol = ctx.template_values['symbol']
    from_address = transfer.parameter.from_
    to_address = transfer.parameter.to
    value = int(transfer.parameter.value)

    from_position, _ = await models.Position.get_or_create(trader=from_address, symbol=symbol)
    from_position.shares_qty -= value
    assert from_position.shares_qty >= 0, transfer.data.hash
    await from_position.save()

    to_position, _ = await models.Position.get_or_create(trader=to_address, symbol=symbol)
    to_position.shares_qty += value
    assert to_position.shares_qty >= 0, transfer.data.hash
    await to_position.save()