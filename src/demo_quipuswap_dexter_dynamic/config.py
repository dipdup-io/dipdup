from dipdup.config import DipDupConfig

from dataclasses import dataclass
import os
from typing import Dict, List
import requests
import json
from ruamel.yaml import YAML

from dipdup.datasources import DatasourceT


@dataclass
class Factory:
    address: str
    template: str


@dataclass
class DEX:
    address: str
    token_address: str
    symbol: str
    decimals: int
    template: str


FACTORIES = [
    Factory('KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD', 'quipuswap_fa12'),
    Factory('KT1SwH9P1Tx8a58Mm6qBExQFTcy2rwZyZiXS', 'quipuswap_fa2'),
]

DEXES = [
    DEX('KT1BGQR7t4izzKZ7eRodKWTodAsM23P38v7N', 'KT1PWx2mnDueood7fEmfbBDKx1D9BAnnXitn', 'tzBTC', 8, 'dexter_fa12'),
]


async def configure(config: DipDupConfig, datasources: Dict[str, DatasourceT]) -> None:
    dexes: List[DEX] = [*DEXES]

    for factory in FACTORIES:
        print(f'Processing factory {factory.address}')

        originated_contracts = requests.get(GET_ORIGINATED_CONTRACTS.format(factory.address)).json()
        originated_contracts_addresses = [c['address'] for c in originated_contracts]

        for dex_address in originated_contracts_addresses:
            print(f'Processing DEX {dex_address}')

            storage = requests.get(GET_STORAGE.format(dex_address)).json()

            token_address = storage['storage']['token_address']

            tokens = requests.get(GET_TOKENS.format(token_address)).json()

            if len(tokens) > 1:
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
                DEX(dex_address, token_address, symbol, decimals, factory.template)
            )

    indexes = {}
    contracts = {}

    for dex in dexes:

        token_contract_name = f'token_{dex.symbol}'
        if token_contract_name not in contracts:
            token_contract_config = {
                'address': dex.token_address,
                'typename': token_contract_name,
            }
            contracts[token_contract_name] = token_contract_config

        dex_contract_name = dex.template + '_' + dex.symbol
        dex_contract_config = {
            'address': dex.address,
            'typename': dex_contract_name,
        }
        contracts[dex_contract_name] = dex_contract_config

        index_name = dex_contract_name
        index_config = {
            'template': dex.template,
            'values': {
                'dex_contract': dex_contract_name,
                'token_contract': token_contract_name,
                'symbol': dex_contract_name,
                'decimals': dex.decimals,
            }
        }
        indexes[index_name] = index_config
