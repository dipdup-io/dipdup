import demo_dex.models as models
from demo_dex.types.quipu_fa2.tezos_parameters.transfer import TransferParameter
from demo_dex.types.quipu_fa2.tezos_storage import QuipuFa2Storage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktTransaction


async def on_fa2_transfer(
    ctx: HandlerContext,
    transfer: TzktTransaction[TransferParameter, QuipuFa2Storage],
) -> None:
    transfer_parameter = transfer.parameter.__root__[0]

    symbol = ctx.template_values['symbol']
    from_address = transfer_parameter.from_
    from_position, _ = await models.Position.get_or_create(trader=from_address, symbol=symbol)

    for transfer_tx in transfer_parameter.txs:
        to_address = transfer_tx.to_
        value = int(transfer_tx.amount)

        from_position.shares_qty -= value
        assert from_position.shares_qty >= 0, transfer.data.hash

        to_position, _ = await models.Position.get_or_create(trader=to_address, symbol=symbol)
        to_position.shares_qty += value
        assert to_position.shares_qty >= 0, transfer.data.hash
        await to_position.save()

    await from_position.save()