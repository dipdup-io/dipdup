from typing import TypedDict, List, Dict, Optional, Union
from dipdup.cli import big_yellow_echo, echo


def prompt_anyof(
    question: str,
    options: tuple[str, ...],
    comments: tuple[str, ...],
    default: int,
) -> tuple[int, str]:
    """Ask user to choose one of the options; returns index and value"""
    import survey
    from tabulate import tabulate

    table = tabulate(zip(options, comments), tablefmt='plain')
    index = survey.routines.select(
        question + '\n', options=table.split('\n'), index=default
    )
    return index, options[index]


# Combined predefined settings for each blockchain type, including detailed indexer configurations
DIPDUP_CONFIG = {
    'evm': {
        'datasources': [
            {'kind': 'evm.subsquid', 'requires_api_key': False,
                'default_url': 'https://v2.archive.subsquid.io/network/ethereum-mainnet', 'name': 'subsquid'},
            {'kind': 'evm.node', 'requires_api_key': True,
                'default_url': 'https://eth-mainnet.g.alchemy.com/v2', 'name': 'node'},
            {'kind': 'abi.etherscan', 'requires_api_key': True,
                'default_url': 'https://api.etherscan.io/api', 'name': 'etherscan'}
        ],
        'contract_kind': 'evm',
        'indexers': {
            'evm.events': {'handler_fields': ['callback', 'contract', 'name'], 'optional_fields': {}},
            'evm.transactions': {'handler_fields': ['callback', 'to', 'method'], 'optional_fields': {'first_level': 'integer'}}
        }
    },
    'tezos': {
        'datasources': [
            {'kind': 'tezos.tzkt', 'requires_api_key': False,
                'default_url': 'https://api.ghostnet.tzkt.io', 'name': 'tzkt'}
        ],
        'contract_kind': 'tezos',
        'indexers': {
            'tezos.big_maps': {'handler_fields': ['callback', 'contract', 'path'], 'optional_fields': {'skip_history': 'select'}},
            'tezos.events': {'handler_fields': ['callback', 'contract', 'tag'], 'optional_fields': {}},
            'tezos.head': {'handler_fields': [], 'optional_fields': {'callback': 'string'}},
            'tezos.operations': {'handler_fields': ['callback', 'pattern'], 'optional_fields': {}},
            'tezos.operations_unfiltered': {'handler_fields': [], 'optional_fields': {'types': 'select', 'callback': 'string', 'first_level': 'integer', 'last_level': 'integer'}},
            'tezos.token_balances': {'handler_fields': ['callback', 'contract'], 'optional_fields': {}},
            'tezos.token_transfers': {'handler_fields': ['callback', 'contract'], 'optional_fields': {}}
        }
    },
    'starknet': {
        'datasources': [
            {'kind': 'starknet.subsquid', 'requires_api_key': False,
                'default_url': 'https://v2.archive.subsquid.io/network/starknet-mainnet', 'name': 'subsquid'},
            {'kind': 'starknet.node', 'requires_api_key': True,
                'default_url': 'https://starknet-mainnet.g.alchemy.com/v2', 'name': 'node'}
        ],
        'contract_kind': 'starknet',
        'indexers': {'starknet.events': {'handler_fields': ['callback', 'contract', 'name'], 'optional_fields': {}}}
    }
}


# TypedDicts for return types
class Pattern(TypedDict):
    destination: str
    entrypoint: str


class Handler(TypedDict):
    name: Optional[str]
    callback: str
    contract: Optional[str]
    path: Optional[str]
    tag: Optional[str]
    pattern: Optional[Pattern]
    to: Optional[str]
    method: Optional[str]


class Datasource(TypedDict):
    name: str
    kind: str
    url: str
    ws_url: Optional[str]
    api_key: Optional[str]


class Contract(TypedDict):
    name: str
    kind: str
    address: str
    typename: str


class Index(TypedDict):
    name: str
    kind: str
    datasources: List[str]
    handlers: Optional[List[Handler]]
    skip_history: Optional[str]
    first_level: Optional[int]
    last_level: Optional[int]
    callback: Optional[str]
    types: Optional[List[str]]
    contracts: Optional[List[str]]


class DipDupYamlConfig(TypedDict):
    datasources: List[Datasource]
    contracts: Optional[List[Contract]]
    indexes: List[Index]


# Helper function to generate comments for datasource options
def get_datasource_comments(datasources: tuple) -> tuple:
    default_comments = {
        'evm.subsquid': 'Use Subsquid as your datasource for EVM.',
        'evm.node': 'Connect to an EVM node.',
        'abi.etherscan': 'Fetch ABI from Etherscan.',
        'tezos.tzkt': 'Use TzKT indexer for Tezos.',
        'starknet.subsquid': 'Use Subsquid for Starknet.',
        'starknet.node': 'Connect to a Starknet node.'
    }
    return tuple(default_comments.get(option, "No description available") for option in datasources)


# Helper function to generate comments for indexers options
def get_indexer_comments(indexers: dict) -> tuple:
    default_comments = {
        'evm.events': 'Listen to EVM blockchain events.',
        'evm.transactions': 'Track EVM blockchain transactions.',
        'tezos.big_maps': 'Monitor changes in Tezos big maps.',
        'tezos.events': 'Track specific events in Tezos.',
        'tezos.head': 'Monitor Tezos chain head updates.',
        'tezos.operations': 'Track operations on Tezos blockchain.',
        'tezos.operations_unfiltered': 'Monitor unfiltered Tezos operations.',
        'tezos.token_balances': 'Track Tezos token balances.',
        'tezos.token_transfers': 'Monitor token transfers on Tezos.',
        'starknet.events': 'Listen to Starknet blockchain events.'
    }
    return tuple(default_comments.get(option, "No description available") for option in indexers)


def query_handlers(contract_names: List[str], additional_fields: List[str] = None) -> Optional[List[Handler]]:
    import survey
    handlers: List[Handler] = []

    if not additional_fields:
        return None

    big_yellow_echo('Configure Indexer Handlers')

    while True:
        handler: Handler = {'callback': None, 'path': None, 'tag': None,
                            'pattern': None, 'name': None, 'contract': None, 'to': None, 'method': None}

        # Prompt for additional fields
        for field in additional_fields:
            if field in ['contract', 'to']:
                handler[field] = prompt_anyof('Choose contract for the handler', tuple(
                    contract_names), ('Contract to listen to',) * len(contract_names), 0)[1]
            elif field == 'pattern':
                handler['pattern'] = {
                    'destination': prompt_anyof('Choose contract for the handler', tuple(contract_names), ('Contract to listen to',) * len(contract_names), 0)[1],
                    'entrypoint': validate_non_empty_input(survey.routines.input('Enter pattern entrypoint: ', value=''), 'entrypoint')
                }
            else:
                handler[field] = validate_non_empty_input(
                    survey.routines.input(f'Enter handler {field}: ', value=''), field)

        handlers.append(handler)

        if survey.routines.input("Add another handler? (y/n): ", value='').lower() != 'y':
            break

    return handlers


def query_optional_fields(optional_fields: Dict[str, str]) -> Dict[str, Optional[Union[str, int]]]:
    import survey
    field_values: Dict[str, Optional[Union[str, int]]] = {}

    for field, field_type in optional_fields.items():
        if field_type == 'select':
            if field == 'types':
                types = []
                while True:
                    _, type = prompt_anyof('Select operation type', (
                        'origination', 'transaction', 'migration'), ('origination', 'transaction', 'migration'), 0)
                    types.append(type)
                    if survey.routines.input("Add another type? (y/n): ", value='').lower() != 'y':
                        break
                field_values[field] = types
            else:
                _, field_values[field] = prompt_anyof(
                    f'Select {field}', ('never', 'always', 'auto'), ('Never', 'Always', 'Auto'), 0)
        else:
            field_values[field] = survey.routines.input(f'Enter {field}: ')

    return field_values


def validate_non_empty_input(input_value: str, field_name: str) -> str:
    import survey
    while not input_value.strip():
        echo(f'{field_name} cannot be empty. Please enter a valid value.', fg='red')
        input_value = survey.routines.input(f'Enter {field_name}: ')
    return input_value


def query_dipdup_config(blockchain: str) -> DipDupYamlConfig:
    import survey

    blockchain_config = DIPDUP_CONFIG[blockchain]

    big_yellow_echo('Configure Datasources')

    datasources: List[Datasource] = []
    datasource_names: List[str] = []

    while True:
        datasource_options = blockchain_config['datasources']
        datasource_comments = get_datasource_comments(
            [ds['kind'] for ds in datasource_options])

        selected_index, datasource_kind = prompt_anyof(f"Select the datasource kind for {
                                                       blockchain}:", tuple(ds['kind'] for ds in datasource_options), datasource_comments, 0)
        selected_datasource = datasource_options[selected_index]

        final_url = validate_non_empty_input(survey.routines.input(
            'Enter Datasource URL: ', value=selected_datasource.get('default_url', '')), 'Datasource URL')
        api_key = None
        ws_url = None

        if selected_datasource['requires_api_key']:
            api_key = validate_non_empty_input(
                survey.routines.input('Enter API key: ', value=''), 'API key')
            if 'node' in datasource_kind:
                final_url = '${NODE_URL:-' + final_url + '}/${NODE_API_KEY:-' + api_key + '}'
                if datasource_kind == 'evm.node':
                    ws_url = survey.routines.input(
                        'Enter WebSocket (wss) URL: ', value='wss://eth-mainnet.g.alchemy.com/v2')
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
        datasource_names.append(datasource['name'])

        if survey.routines.input("Add another datasource? (y/n): ", value='').lower() != 'y':
            break

    big_yellow_echo('Configure Contracts')

    contracts: List[Contract] = []
    contract_names: List[str] = []

    while True:
        contract_name = validate_non_empty_input(
            survey.routines.input('Enter contract name: '), 'Contract name')
        contract_address = validate_non_empty_input(
            survey.routines.input('Enter contract address: '), 'Contract address')

        contract: Contract = {
            'name': contract_name,
            'kind': blockchain_config['contract_kind'],
            'address': contract_address,
            'typename': contract_name
        }

        contracts.append(contract)
        contract_names.append(contract['name'])

        if survey.routines.input("Add another contract? (y/n): ", value='').lower() != 'y':
            break

    big_yellow_echo('Configure Indexers')

    indexes: List[Index] = []

    while True:
        indexer_options = tuple(blockchain_config['indexers'].keys())
        indexer_comments = get_indexer_comments(blockchain_config['indexers'])

        indexer = prompt_anyof(f"Select the type of index for {
                               blockchain}:", indexer_options, indexer_comments, 0)[1]

        index_config = blockchain_config['indexers'].get(indexer, {})
        index_name = validate_non_empty_input(
            survey.routines.input('Enter the indexer name: '), 'Indexer name')

        index: Index = {
            'name': index_name,
            'kind': indexer,
            'datasources': datasource_names,
            'handlers': None,
            'skip_history': None,
            'first_level': None,
            'last_level': None,
            'callback': None,
            'types': None,
            'contracts': None
        }

        handlers = query_handlers(
            contract_names, index_config.get('handler_fields'))
        index['handlers'] = handlers

        if 'optional_fields' in index_config:
            index.update(query_optional_fields(
                index_config['optional_fields']))

        indexes.append(index)

        if survey.routines.input("Add another indexer? (y/n): ", value='').lower() != 'y':
            break

    return DipDupYamlConfig(
        datasources=datasources,
        contracts=contracts,
        indexes=indexes
    )
