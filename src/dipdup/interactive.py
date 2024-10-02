from typing import TypedDict, List, Dict, Optional, Union


def prompt_anyof(
    question: str,
    options: tuple[str, ...],
    comments: tuple[str, ...],
    default: int,
) -> tuple[int, str]:
    """Ask user to choose one of options; returns index and value"""
    import survey  # type: ignore[import-untyped]
    from tabulate import tabulate

    table = tabulate(
        zip(options, comments, strict=True),
        tablefmt='plain',
    )
    index = survey.routines.select(
        question + '\n',
        options=table.split('\n'),
        index=default,
    )
    return index, options[index]


# Combined predefined settings for each blockchain type, including detailed indexer configurations
DIPDUP_CONFIG = {
    'evm': {
        'datasources': ('evm.subsquid', 'evm.node', 'abi.etherscan'),
        'contract_kind': 'evm',
        'indexers': {
            'evm.events': {
                'handler_fields': [],
                'optional_fields': {}  # No optional fields for evm.events
            },
            'evm.transactions': {
                'handler_fields': [],
                # Specific optional fields
                'optional_fields': {'first_level': 'integer'}
            }
        }
    },
    'tezos': {
        'datasources': ('tezos.tzkt',),
        'contract_kind': 'tezos',
        'indexers': {
            'tezos.big_maps': {
                # Additional handler fields for big_maps
                'handler_fields': ['path'],
                # Optional fields for big_maps
                'optional_fields': {'skip_history': 'select'}
            },
            'tezos.events': {
                'handler_fields': ['tag'],
                'optional_fields': {}  # No optional fields for tezos.events
            },
            'tezos.head': {
                'handler_fields': [],
                'optional_fields': {'callback': 'string'}
            },
            'tezos.operations': {
                'handler_fields': ['pattern'],
                'optional_fields': {}  # No optional fields for tezos.operations
            },
            'tezos.operations_unfiltered': {
                'handler_fields': [],
                'optional_fields': {'types': 'select', 'first_level': 'integer', 'last_level': 'integer'}
            },
            'tezos.token_balances': {
                'handler_fields': [],
                'optional_fields': {}
            },
            'tezos.token_transfers': {
                'handler_fields': [],
                'optional_fields': {}
            }
        }
    },
    'starknet': {
        'datasources': ('starknet.subsquid', 'starknet.node'),
        'contract_kind': 'starknet',
        'indexers': {
            'starknet.events': {
                'handler_fields': [],
                'optional_fields': {}  # No optional fields for starknet.events
            }
        }
    }
}


# TypedDicts for return types
class Handler(TypedDict):
    callback: str
    contract: str
    path: Optional[str]
    tag: Optional[str]
    pattern: Optional[List[Dict[str, str]]]  # For tezos.operations


class Datasource(TypedDict):
    name: str
    kind: str
    url: str
    api_key: Optional[str]


class Contract(TypedDict):
    name: str
    kind: str
    address: str
    typename: str


class Index(TypedDict):
    kind: str
    datasources: List[str]
    handlers: List[Handler]
    skip_history: Optional[str]  # For tezos.big_maps
    # For evm.transactions or tezos.operations_unfiltered
    first_level: Optional[int]
    last_level: Optional[int]    # For tezos.operations_unfiltered
    callback: Optional[str]      # For tezos.head
    types: Optional[List[str]]   # For tezos.operations_unfiltered
    contracts: Optional[List[str]]  # For tezos.operations


class DipDupConfig(TypedDict):
    datasources: List[Datasource]
    contracts: List[Contract]
    indexes: List[Index]


# Helper functions with typings
def query_handlers(contract_names: List[str], additional_fields: Optional[List[str]] = None) -> List[Handler]:
    import survey
    handlers: List[Handler] = []

    while True:
        handler: Handler = {
            'callback': survey.routines.input('Enter the callback name for the handler: '),
            'contract': prompt_anyof('Choose contract for the handler', tuple(contract_names), (), 0)[1],
            'path': None,
            'tag': None,
            'pattern': None
        }

        if additional_fields:
            for field in additional_fields:
                handler[field] = survey.routines.input(
                    f"Enter {field}: ", value=handler.get(field))

        handlers.append(handler)

        if survey.routines.input("Add another handler? (y/n): ", value='y').lower() != 'y':
            break

    return handlers


def query_optional_fields(optional_fields: Dict[str, str]) -> Dict[str, Optional[Union[str, int]]]:
    import survey
    field_values: Dict[str, Optional[Union[str, int]]] = {}

    for field, field_type in optional_fields.items():
        if field_type == 'select':
            _, field_values[field] = prompt_anyof(
                f'Select {field}', ('never', 'always', 'auto'), (), 0)
        else:
            field_values[field] = survey.routines.input(f'Enter {field}: ')

    return field_values


# Main function with full typings
def query_dipdup_config(blockchain: str) -> DipDupConfig:
    import survey

    # Accessing blockchain-specific config
    blockchain_config = DIPDUP_CONFIG[blockchain]

    # Query for datasources
    datasources: List[Datasource] = []
    # To store datasource names for later use in indexes
    datasource_names: List[str] = []

    while True:
        datasource: Datasource = {
            'name': survey.routines.input('Enter Datasource name: '),
            'kind': prompt_anyof(f"Select the datasource kind for {blockchain}:", tuple(blockchain_config['datasources']), (), 0)[1],
            'url': survey.routines.input('Enter Datasource URL: '),
            'api_key': survey.routines.input('Enter API key: ', value=None)
        }

        datasources.append(datasource)
        datasource_names.append(datasource['name'])

        if survey.routines.input("Add another datasource? (y/n): ", value='y').lower() != 'y':
            break

    # Query for contracts
    contracts: List[Contract] = []
    # To store contract names for handlers in indexes
    contract_names: List[str] = []

    while True:
        contract: Contract = {
            'name': survey.routines.input('Enter contract name: '),
            'kind': blockchain_config['contract_kind'],
            'address': survey.routines.input('Enter contract address: '),
            'typename': survey.routines.input('Enter contract typename: ')
        }

        contracts.append(contract)
        contract_names.append(contract['name'])

        if survey.routines.input("Add another contract? (y/n): ", value='y').lower() != 'y':
            break

    # Query for indexes
    indexes: List[Index] = []

    while True:
        index_kind = prompt_anyof(f"Select the type of index for {blockchain}:", tuple(
            blockchain_config['index_kinds']), (), 0)[1]
        index_config = blockchain_config['indexers'].get(index_kind, {})

        index: Index = {
            'kind': index_kind,
            'datasources': datasource_names,
            'handlers': query_handlers(contract_names, index_config.get('handler_fields')),
            'skip_history': None,
            'first_level': None,
            'last_level': None,
            'callback': None,
            'types': None,
            'contracts': None
        }

        if 'optional_fields' in index_config:
            index.update(query_optional_fields(
                index_config['optional_fields']))

        indexes.append(index)

        if survey.routines.input("Add another index? (y/n): ", value='y').lower() != 'y':
            break

    # Return final DipDup configuration
    return DipDupConfig(
        datasources=datasources,
        contracts=contracts,
        indexes=indexes
    )
