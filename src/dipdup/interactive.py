from typing import Any
from typing import TypedDict

import survey  # type: ignore[import-untyped]

from dipdup.cli import big_yellow_echo
from dipdup.cli import echo
from dipdup.install import ask


class Pattern(TypedDict):
    destination: str
    entrypoint: str


class Handler(TypedDict):
    name: str | None
    callback: str | None
    contract: str | None
    path: str | None
    tag: str | None
    pattern: Pattern | None
    to: str | None
    method: str | None


class Datasource(TypedDict):
    name: str
    kind: str
    url: str
    ws_url: str | None
    api_key: str | None


class Contract(TypedDict):
    name: str
    kind: str
    address: str
    typename: str


class Index(TypedDict):
    name: str
    kind: str
    datasources: list[str]
    handlers: list[Handler] | None
    skip_history: str | None
    first_level: int | None
    last_level: int | None
    callback: str | None
    types: list[str] | None
    contracts: list[str] | None


class DipDupSurveyConfig(TypedDict):
    datasources: list[Datasource]
    contracts: list[Contract] | None
    indexes: list[Index]


class DatasourceConfig(TypedDict):
    kind: str
    requires_api_key: bool
    default_url: str
    name: str


class IndexerConfig(TypedDict):
    handler_fields: list[str]
    optional_fields: dict[str, str | int]
    kind: str


class BlockchainConfig(TypedDict):
    datasources: list[DatasourceConfig]
    contract_kind: str
    indexers: dict[str, IndexerConfig]


# Example instantiation
CONFIG_STRUCTURE: dict[str, BlockchainConfig] = {
    'evm': {
        'datasources': [
            {
                'kind': 'evm.subsquid',
                'requires_api_key': False,
                'default_url': 'https://v2.archive.subsquid.io/network/ethereum-mainnet',
                'name': 'subsquid',
            },
            {
                'kind': 'evm.node',
                'requires_api_key': True,
                'default_url': 'https://eth-mainnet.g.alchemy.com/v2',
                'name': 'node',
            },
            {
                'kind': 'abi.etherscan',
                'requires_api_key': True,
                'default_url': 'https://api.etherscan.io/api',
                'name': 'etherscan',
            },
        ],
        'contract_kind': 'evm',
        'indexers': {
            'events': {
                'handler_fields': ['callback', 'contract', 'name'],
                'optional_fields': {},
                'kind': 'evm.events',
            },
            'transactions': {
                'handler_fields': ['callback', 'to', 'method'],
                'optional_fields': {
                    'first_level': 'integer',
                },
                'kind': 'evm.transactions',
            },
        },
    },
    'tezos': {
        'datasources': [
            {
                'kind': 'tezos.tzkt',
                'requires_api_key': False,
                'default_url': 'https://api.ghostnet.tzkt.io',
                'name': 'tzkt',
            }
        ],
        'contract_kind': 'tezos',
        'indexers': {
            'big_maps': {
                'handler_fields': ['callback', 'contract', 'path'],
                'optional_fields': {
                    'skip_history': 'select',
                },
                'kind': 'tezos.big_maps',
            },
            'events': {
                'handler_fields': ['callback', 'contract', 'tag'],
                'optional_fields': {},
                'kind': 'tezos.events',
            },
            'head': {
                'handler_fields': [],
                'optional_fields': {
                    'callback': 'string',
                },
                'kind': 'tezos.head',
            },
            'operations': {
                'handler_fields': ['callback', 'pattern'],
                'optional_fields': {},
                'kind': 'tezos.operations',
            },
            'operations_unfiltered': {
                'handler_fields': [],
                'optional_fields': {
                    'types': 'select',
                    'callback': 'string',
                    'first_level': 'integer',
                    'last_level': 'integer',
                },
                'kind': 'tezos.operations_unfiltered',
            },
            'token_balances': {
                'handler_fields': ['callback', 'contract'],
                'optional_fields': {},
                'kind': 'tezos.token_balances',
            },
            'token_transfers': {
                'handler_fields': ['callback', 'contract'],
                'optional_fields': {},
                'kind': 'tezos.token_transfers',
            },
        },
    },
    'starknet': {
        'datasources': [
            {
                'kind': 'starknet.subsquid',
                'requires_api_key': False,
                'default_url': 'https://v2.archive.subsquid.io/network/starknet-mainnet',
                'name': 'subsquid',
            },
            {
                'kind': 'starknet.node',
                'requires_api_key': True,
                'default_url': 'https://starknet-mainnet.g.alchemy.com/v2',
                'name': 'node',
            },
        ],
        'contract_kind': 'starknet',
        'indexers': {
            'events': {
                'handler_fields': ['callback', 'contract', 'name'],
                'optional_fields': {},
                'kind': 'starknet.events',
            }
        },
    },
}


def prompt_anyof(
    question: str,
    options: tuple[str, ...],
    comments: tuple[str, ...],
    default: int,
) -> tuple[int, str]:
    """Ask user to choose one of the options; returns index and value"""
    from tabulate import tabulate

    table = tabulate(
        zip(options, comments, strict=False),
        tablefmt='plain',
    )
    index = survey.routines.select(
        question + '\n',
        options=table.split('\n'),
        index=default,
    )
    return index, options[index]


# Helper function to generate comments for datasource options
def get_datasource_comments(datasources: list[str]) -> tuple[str, ...]:
    default_comments = {
        'evm.subsquid': 'Use Subsquid as your datasource for EVM.',
        'evm.node': 'Connect to an EVM node.',
        'abi.etherscan': 'Fetch ABI from Etherscan.',
        'tezos.tzkt': 'Use TzKT indexer for Tezos.',
        'starknet.subsquid': 'Use Subsquid for Starknet.',
        'starknet.node': 'Connect to a Starknet node.',
    }
    return tuple(default_comments.get(option, 'No description available') for option in datasources)


# Helper function to generate comments for indexers options
def get_indexer_comments(indexers: dict[str, IndexerConfig]) -> tuple[str, ...]:
    default_comments: dict[str, str] = {
        'evm.events': 'Listen to EVM blockchain events.',
        'evm.transactions': 'Track EVM blockchain transactions.',
        'tezos.big_maps': 'Monitor changes in Tezos big maps.',
        'tezos.events': 'Track specific events in Tezos.',
        'tezos.head': 'Monitor Tezos chain head updates.',
        'tezos.operations': 'Track operations on Tezos blockchain.',
        'tezos.operations_unfiltered': 'Monitor unfiltered Tezos operations.',
        'tezos.token_balances': 'Track Tezos token balances.',
        'tezos.token_transfers': 'Monitor token transfers on Tezos.',
        'starknet.events': 'Listen to Starknet blockchain events.',
    }
    comments = []
    for _, config in indexers.items():
        kind = config.get('kind')
        comment = default_comments.get(kind, 'No description available')  # type: ignore
        comments.append(comment)
    return tuple(comments)


def query_handlers(
    contract_names: list[str],
    additional_fields: list[str] | None,
) -> list[Handler] | None:

    handlers: list[Handler] = []

    if not additional_fields:
        return None

    big_yellow_echo('Configure Indexer Handlers')

    while True:
        handler: Handler = {
            'callback': '',
            'path': None,
            'tag': None,
            'pattern': None,
            'name': None,
            'contract': None,
            'to': None,
            'method': None,
        }

        # Prompt for additional fields
        for field in additional_fields:
            if field in ['contract', 'to']:
                handler[field] = prompt_anyof(  # type: ignore
                    'Choose contract for the handler',
                    tuple(contract_names),
                    ('Contract to listen to',) * len(contract_names),
                    0,
                )[1]
            elif field == 'pattern':
                handler['pattern'] = {
                    'destination': prompt_anyof(
                        'Choose contract for the handler',
                        tuple(contract_names),
                        ('Contract to listen to',) * len(contract_names),
                        0,
                    )[1],
                    'entrypoint': validate_non_empty_input(
                        survey.routines.input('Enter pattern entrypoint: ', value=''), 'entrypoint'
                    ),
                }
            else:
                handler[field] = validate_non_empty_input(  # type: ignore
                    survey.routines.input(f'Enter handler {field}: ', value=''),
                    field,
                )

        handlers.append(handler)

        if not ask('Add another handler?', False):
            break

    return handlers


def query_optional_fields(optional_fields: dict[str, str | int]) -> dict[str, Any]:
    field_values: dict[str, Any] = {}
    for field, field_type in optional_fields.items():
        if field_type == 'select':
            if field == 'types':
                types: list[str] = []
                while True:
                    _, type = prompt_anyof(
                        'Select operation type',
                        ('origination', 'transaction', 'migration'),
                        ('origination', 'transaction', 'migration'),
                        0,
                    )
                    types.append(type)
                    if not ask('Add another type?', False):
                        break
                field_values[field] = types
            else:
                _, field_values[field] = prompt_anyof(
                    f'Select {field}',
                    ('never', 'always', 'auto'),
                    ('Never', 'Always', 'Auto'),
                    0,
                )
        else:
            field_values[field] = survey.routines.input(f'Enter {field}: ')

    return field_values


def validate_non_empty_input(input_value: str, field_name: str) -> str:
    while not input_value.strip():
        echo(f'{field_name} cannot be empty. Please enter a valid value.', fg='red')
        input_value = survey.routines.input(f'Enter {field_name}: ')
    return input_value


def filter_indexer_options(
    indexers: tuple[str, ...],
    indexer_comments: tuple[str, ...],
    contracts: list[Contract],
    blockchain: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    blockchain_config = CONFIG_STRUCTURE[blockchain]
    indexer_dict = blockchain_config['indexers']
    required_contract_fields = {'contract', 'to', 'pattern'}
    if not contracts:
        valid_indexes = [
            idx
            for idx, indexer in enumerate(indexers)
            if not required_contract_fields.intersection(set(indexer_dict[indexer].get('handler_fields', [])))
            or contracts
        ]

        indexers = tuple(indexers[idx] for idx in valid_indexes)
        indexer_comments = tuple(indexer_comments[idx] for idx in valid_indexes)

    return indexers, indexer_comments


def query_dipdup_config(blockchain: str) -> DipDupSurveyConfig:

    blockchain_config = CONFIG_STRUCTURE[blockchain]

    datasources: list[Datasource] = []
    contracts: list[Contract] = []
    indexes: list[Index] = []

    big_yellow_echo('Configure DipDup Project Setup')

    if ask('Add datasource?', True):
        while True:
            datasource_options = blockchain_config['datasources']
            datasource_comments = get_datasource_comments([ds['kind'] for ds in datasource_options])

            selected_index, _ = prompt_anyof(
                f'Select the datasource kind for {blockchain}:',
                tuple(ds['name'] for ds in datasource_options),
                datasource_comments,
                0,
            )
            selected_datasource = datasource_options[selected_index]
            datasource_kind = selected_datasource['kind']

            final_url = validate_non_empty_input(
                survey.routines.input('Enter Datasource URL: ', value=selected_datasource.get('default_url', '')),
                'Datasource URL',
            )
            api_key = None
            ws_url = None

            if selected_datasource['requires_api_key']:
                api_key = validate_non_empty_input(
                    survey.routines.input('Enter API key: ', value=''),
                    'API key',
                )
                if 'node' in datasource_kind:
                    final_url = '${NODE_URL:-' + final_url + '}/${NODE_API_KEY:-' + api_key + '}'
                    if datasource_kind == 'evm.node':
                        ws_url = survey.routines.input(
                            'Enter WebSocket (wss) URL: ', value='wss://eth-mainnet.g.alchemy.com/v2'
                        )
                        ws_url = '${NODE_WS_URL:-' + ws_url + '}/${NODE_API_KEY:-' + api_key + '}'
                    api_key = None
                else:
                    api_key = '${ETHERSCAN_API_KEY:-' + api_key + '}'

            if datasource_kind != 'abi.etherscan':
                api_key = None

            if 'subsquid' in datasource_kind:
                final_url = '${SUBSQUID_URL:-' + final_url + '}'

            datasource: Datasource = {
                'kind': datasource_kind,
                'url': final_url,
                'ws_url': ws_url,
                'api_key': api_key,
                'name': selected_datasource.get('name', 'dipDUp'),
            }

            datasources.append(datasource)

            if not ask('Add another datasource?', False):
                break

    if ask('Add contract?', True):
        while True:
            contract_name = validate_non_empty_input(
                survey.routines.input('Enter contract name: '),
                'Contract name',
            )
            contract_address = validate_non_empty_input(
                survey.routines.input('Enter contract address: '),
                'Contract address',
            )

            contract: Contract = {
                'name': contract_name,
                'kind': blockchain_config['contract_kind'],
                'address': contract_address,
                'typename': contract_name,
            }

            contracts.append(contract)

            if not ask('Add another contract?', False):
                break

    if datasources:
        indexer_options = tuple(blockchain_config['indexers'].keys())
        indexer_comments = get_indexer_comments(blockchain_config['indexers'])

        indexer_options, indexer_comments = filter_indexer_options(
            indexer_options, indexer_comments, contracts, blockchain
        )

        if indexer_options and ask('Add indexer?', True):
            while True:
                indexer = prompt_anyof(
                    f'Select the type of indexer for {blockchain}:', indexer_options, indexer_comments, 0
                )[1]

                index_config = blockchain_config['indexers'][indexer]
                index_name = validate_non_empty_input(survey.routines.input('Enter the indexer name: '), 'Indexer name')

                index: Index = {
                    'name': index_name,
                    'kind': index_config['kind'],
                    'datasources': [ds['name'] for ds in datasources],
                    'handlers': None,
                    'skip_history': None,
                    'first_level': None,
                    'last_level': None,
                    'callback': None,
                    'types': None,
                    'contracts': None,
                }

                handlers = query_handlers([c['name'] for c in contracts], index_config.get('handler_fields'))
                index['handlers'] = handlers

                if 'optional_fields' in index_config:
                    index.update(query_optional_fields(index_config['optional_fields']))  # type: ignore

                indexes.append(index)

                if not ask('Add another indexer?', False):
                    break

    return DipDupSurveyConfig(
        datasources=datasources,
        contracts=contracts,
        indexes=indexes,
    )
