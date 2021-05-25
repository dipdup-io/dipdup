from pydantic import BaseModel
from dipdup.config import ContractConfig, DipDupConfig, StaticTemplateConfig

from typing import Dict, List, cast

from dipdup.datasources import DatasourceT
from dipdup.datasources.bcd.datasource import BcdDatasource
from dipdup.datasources.tzkt.datasource import TzktDatasource


class Factory(BaseModel):
    address: str
    template: str


class DEX(BaseModel):
    address: str
    token_address: str
    symbol: str
    decimals: int
    template: str


async def configure(config: DipDupConfig, datasources: Dict[str, DatasourceT]) -> None:
    assert config.configuration
    args = config.configuration.args
    tzkt = cast(TzktDatasource, datasources[args['tzkt']])
    bcd = cast(BcdDatasource, datasources[args['bcd']])

    dexes: List[DEX] = [DEX.parse_obj(d) for d in args['dexes']]
    factories: List[Factory] = [Factory.parse_obj(f) for f in args['factories']]

    for factory in factories:
        print(f'Processing factory {factory.address}')

        originated_contracts = await tzkt.get_originated_contracts(factory.address)

        for dex_address in originated_contracts:
            print(f'Processing DEX {dex_address}')

            storage = await tzkt.get_contract_storage(dex_address)

            token_address = storage['storage']['token_address']

            tokens = await bcd.get_tokens(token_address)

            if tokens and len(tokens) > 1:
                continue

            if tokens:
                symbol = tokens[0]['symbol']
                decimals = tokens[0].get('decimals', 0)
            else:
                try:
                    symbol = storage['symbol']
                    decimals = storage.get('decimals', 0)
                except Exception:
                    continue

            dexes.append(
                DEX(
                    address=dex_address,
                    token_address=token_address,
                    symbol=symbol,
                    decimals=decimals,
                    template=factory.template,
                )
            )

    for dex in dexes:

        token_contract_name = f'token_{dex.symbol}'
        if token_contract_name not in config.contracts:
            token_contract_config = ContractConfig(
                address=dex.token_address,
                typename=token_contract_name,
            )
            config.contracts[token_contract_name] = token_contract_config

        dex_contract_name = dex.template + '_' + dex.symbol
        if dex_contract_name not in config.contracts:
            dex_contract_config = ContractConfig(
                address=dex.address,
                typename=dex_contract_name,
            )
            config.contracts[dex_contract_name] = dex_contract_config

        index_name = dex_contract_name
        if index_name not in config.indexes:
            index_config = StaticTemplateConfig(
                template=dex.template,
                values=dict(
                    dex_contract=dex_contract_name,
                    token_contract=token_contract_name,
                    symbol=dex_contract_name,
                    decimals=str(dex.decimals),
                )
            )
            config.indexes[index_name] = index_config
