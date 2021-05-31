from contextlib import suppress
from datetime import datetime, timedelta
import logging
from typing import Dict, List, cast

from pydantic import BaseModel
from tortoise.exceptions import OperationalError
from tortoise.transactions import in_transaction

from dipdup.config import ContractConfig, DipDupConfig, StaticTemplateConfig
from dipdup.datasources import DatasourceT
from dipdup.datasources.bcd.datasource import BcdDatasource
from dipdup.datasources.tzkt.datasource import TzktDatasource

_logger = logging.getLogger(__name__)


class Factory(BaseModel):
    address: str
    exchange: str
    standard: str


class DEX(BaseModel):
    address: str
    exchange: str
    standard: str

    token_address: str
    symbol: str
    decimals: int


async def update_totals(interval: int) -> None:
    async with in_transaction() as conn:
        with suppress(OperationalError):
            updated_at = datetime.utcfromtimestamp((await conn.execute_query('SELECT updated_at FROM trade_total LIMIT 1'))[0])
            if datetime.now() - updated_at < timedelta(seconds=interval):
                return

    async with in_transaction() as conn:
        with suppress(OperationalError):
            await conn.execute_query('CALL trade_summary()')


async def configure(config: DipDupConfig, datasources: Dict[str, DatasourceT]) -> None:
    assert config.configuration
    args = config.configuration.args
    include = args.get('include', [])
    exclude = args.get('exclude', [])
    tzkt = cast(TzktDatasource, datasources[args['tzkt']])
    bcd = cast(BcdDatasource, datasources[args['bcd']])

    await update_totals(int(args['update_totals_interval']))

    dexes: List[DEX] = [DEX.parse_obj(d) for d in args['dexes']]
    factories: List[Factory] = [Factory.parse_obj(f) for f in args['factories']]

    for factory in factories:
        _logger.info('Processing factory %s', factory.address)

        originated_contracts = await tzkt.get_originated_contracts(factory.address)

        for dex_address in originated_contracts:
            _logger.info('Processing DEX %s', dex_address)

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
                    exchange=factory.exchange,
                    standard=factory.standard,
                    token_address=token_address,
                    symbol=symbol,
                    decimals=decimals,
                )
            )

    for dex in dexes:

        token_contract_typename = f'token_{dex.standard}'
        token_contract_name = f'{token_contract_typename}_{dex.symbol}'

        dex_contract_typename = f'{dex.exchange}_{dex.standard}'
        dex_contract_name = f'{dex_contract_typename}_{dex.symbol}'

        index_name = dex_contract_name
        if (include and index_name not in include) or index_name in exclude:
            continue

        if token_contract_name not in config.contracts:
            token_contract_config = ContractConfig(
                address=dex.token_address,
                typename=token_contract_typename,
            )
            config.contracts[token_contract_name] = token_contract_config

        if dex_contract_name not in config.contracts:
            dex_contract_config = ContractConfig(
                address=dex.address,
                typename=dex_contract_typename,
            )
            config.contracts[dex_contract_name] = dex_contract_config

        if index_name not in config.indexes:
            template = f'{dex.exchange}_{dex.standard}'
            index_config = StaticTemplateConfig(
                template=template,
                values=dict(
                    dex_contract=dex_contract_name,
                    token_contract=token_contract_name,
                    symbol=dex_contract_name,
                    decimals=str(dex.decimals),
                ),
            )
            config.indexes[index_name] = index_config
