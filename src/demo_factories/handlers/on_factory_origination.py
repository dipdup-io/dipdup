from contextlib import suppress
from typing import cast

from dipdup.context import HandlerContext
from dipdup.exceptions import ContractAlreadyExistsError
from dipdup.models.tezos_tzkt import TzktOperationData


async def on_factory_origination(
    ctx: HandlerContext,
    transaction_0: TzktOperationData,
    origination_1: TzktOperationData,
) -> None:
    assert transaction_0.parameter_json
    dex_contract = cast(str, origination_1.originated_contract_address)
    token_contract = cast(str, transaction_0.parameter_json['token']['address'])

    await ctx.add_contract(
        kind='tezos',
        name=dex_contract,
        address=dex_contract,
        typename='dex',
    )
    with suppress(ContractAlreadyExistsError):
        await ctx.add_contract(
            kind='tezos',
            name=token_contract,
            address=token_contract,
            typename='token',
        )
    await ctx.add_index(
        name=dex_contract,
        template='dex',
        values={
            'dex': dex_contract,
            'token': token_contract,
        }
    )