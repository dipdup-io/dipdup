from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from dipdup.config import DipDupConfig
from dipdup.config.substrate import SubstrateRuntimeConfig
from dipdup.exceptions import FrameworkException
from dipdup.package import DipDupPackage
from dipdup.runtimes import SubstrateRuntime, SubstrateSpecVersion
from dipdup.runtimes import extract_multilocation_payload
from dipdup.runtimes import extract_subsquid_payload




def create_test_runtime() -> SubstrateRuntime:
    """Create a test SubstrateRuntime instance with mocked dependencies."""
    config = SubstrateRuntimeConfig(type_registry='hydradx')
    config._name = 'test'
    package = DipDupPackage(Path(__file__).parent.parent.parent / 'src' / 'demo_substrate_events')
    return SubstrateRuntime(config, package, None)


def setup_runtime_mocks(
    runtime: SubstrateRuntime, event_abi: dict[str, Any]) -> tuple[Mock, Mock]:
    """Setup common mocks for SubstrateRuntime testing."""
    # Mock spec version and event ABI
    spec_version_mock = SubstrateSpecVersion(
        name='1000',
        metadata=[
            {
                'name': 'AssetRegistry',
                'events': [
                    event_abi
                ],
            },
        ]
    )
    # spec_version_mock.get_event_abi.return_value = event_abi
    runtime.get_spec_version = Mock(return_value=spec_version_mock)  # type: ignore[method-assign]


path_1 = [
    [
        {
            'parents': 0,
            'interior': {
                '__kind': 'X2',
                'value': [
                    {
                        '__kind': 'PalletInstance',
                        'value': 50,
                    },
                    {
                        '__kind': 'GeneralIndex',
                        'value': '1337',
                    },
                ],
            },
        },
        84640,
    ],
    [
        {
            'parents': 1,
            'interior': {
                '__kind': 'Here',
            },
        },
        122612710,
    ],
]
path_2 = [
    {
        'interior': {
            '__kind': 'X3',
            'value': [
                {'__kind': 'Parachain', 'value': 1000},
                {'__kind': 'GeneralIndex', 'value': 50},
                {'__kind': 'GeneralIndex', 'value': 42069},
            ],
        },
        'parents': 1,
    }
]

path_3 = [
    {
        'interior': {
            '__kind': 'X3',
            'value': [
                {'__kind': 'Parachain', 'value': 2004},
                {'__kind': 'PalletInstance', 'value': 110},
                {'__kind': 'AccountKey20', 'key': 39384093},
            ],
        },
        'parents': 1,
    }
]

subsquid_general_key_with_value_payload_example = {
    'parents': 1,
    'interior': {
        '__kind': 'X2',
        'value': [
            {'__kind': 'Parachain', 'value': 2030},
            {
                '__kind': 'GeneralKey',
                'value': '0x02c80084af223c8b598536178d9361dc55bfda6818',
            },
        ],
    },
}
subsquid_general_key_with_data_and_length_payload_example = {
    'parents': 1,
    'interior': {
        '__kind': 'X2',
        'value': [
            {'__kind': 'Parachain', 'value': 2030},
            {
                '__kind': 'GeneralKey',
                'data': '0x0809000000000000000000000000000000000000000000000000000000000000',
                'length': 2,
            },
        ],
    },
}


processed_path_1 = (
    (
        {
            'parents': 0,
            'interior': {
                'X2': (
                    {'PalletInstance': 50},
                    {'GeneralIndex': '1337'},
                ),
            },
        },
        84640,
    ),
    (
        {
            'parents': 1,
            'interior': 'Here',
        },
        122612710,
    ),
)

processed_path_2 = (
    {
        'parents': 1,
        'interior': {
            'X3': (
                {'Parachain': 1000},
                {'GeneralIndex': 50},
                {'GeneralIndex': 42069},
            ),
        },
    },
)

processed_path_3 = (
    {
        'parents': 1,
        'interior': {
            'X3': (
                {'Parachain': 2004},
                {'PalletInstance': 110},
                {'AccountKey20': 39384093},
            ),
        },
    },
)
node_general_key_with_value_payload_example = {
    'parents': 1,
    'interior': {
        'X2': (
            {'Parachain': 2030},
            {'GeneralKey': '0x02c80084af223c8b598536178d9361dc55bfda6818'},
        ),
    },
}
node_general_key_with_data_and_length_payload_example = {
    'parents': 1,
    'interior': {
        'X2': (
            {'Parachain': 2030},
            {
                'GeneralKey': {
                    'data': '0x0809000000000000000000000000000000000000000000000000000000000000',
                    'length': 2,
                }
            },
        ),
    },
}

extracted_path_1 = (
    (
        {
            'parents': 0,
            'interior': (
                {'PalletInstance': 50},
                {'GeneralIndex': '1337'},
            ),
        },
        84640,
    ),
    (
        {
            'parents': 1,
            'interior': 'Here',
        },
        122612710,
    ),
)


@pytest.mark.parametrize(
    'subsquid_payload, expected_node_payload',
    (
        (path_1, processed_path_1),
        (path_2, processed_path_2),
        (path_3, processed_path_3),
        (
            subsquid_general_key_with_value_payload_example,
            node_general_key_with_value_payload_example,
        ),
        (
            subsquid_general_key_with_data_and_length_payload_example,
            node_general_key_with_data_and_length_payload_example,
        ),
    ),
)
def test_extract_subsquid_payload(subsquid_payload, expected_node_payload) -> None:  # type: ignore
    assert extract_subsquid_payload(subsquid_payload) == expected_node_payload


def test_extract_multilocation_payload() -> None:
    assert extract_multilocation_payload(processed_path_1) == extracted_path_1


updated_abi_3301 =       {
        "lookup": "3301",
        "name": "Updated",
        "docs": [
          "Asset was updated."
        ],
        "args": [
          "U32",
          "Vec<U8>",
          "pallet_asset_registry:types:AssetType",
          "U128",
          "option<U128>"
        ],
        "args_name": [
          "asset_id",
          "asset_name",
          "asset_type",
          "existential_deposit",
          "xcm_rate_limit"
        ],
        "args_type_name": [
          "AssetId",
          "BoundedVec<u8, StringLimit>",
          "AssetType<AssetId>",
          "Balance",
          "Option<Balance>"
        ]
      }

updated_abi_3302  =    {
        "lookup": "3302",
        "name": "Updated",
        "docs": [
          "Asset was updated."
        ],
        "args": [
          "U32",
          "option<bounded_collections:bounded_vec:BoundedVec@194>",
          "pallet_asset_registry:types:AssetType",
          "U128",
          "option<U128>",
          "option<bounded_collections:bounded_vec:BoundedVec@194>",
          "option<U8>",
          "Bool"
        ],
        "args_name": [
          "asset_id",
          "asset_name",
          "asset_type",
          "existential_deposit",
          "xcm_rate_limit",
          "symbol",
          "decimals",
          "is_sufficient"
        ],
        "args_type_name": [
          "AssetId",
          "Option<BoundedVec<u8, StringLimit>>",
          "AssetType",
          "Balance",
          "Option<Balance>",
          "Option<BoundedVec<u8, StringLimit>>",
          "Option<u8>",
          "bool"
        ]
      }



class TestSubstrateRuntimeDecodeEventArgs:
    """Test cases for SubstrateRuntime.decode_event_args method."""

    def test_decode_event_args_assets_updated_event(self) -> None:
        runtime = create_test_runtime()

        event_abi = updated_abi_3302

        setup_runtime_mocks(runtime, event_abi)

        args = {
            'asset_id': 69,
            'asset_name': '0x47494741444f54',
            'asset_type': {'__kind': 'Erc20'},
            'decimals': 18,
            'existential_deposit': '1000000000000000000',  # 1 token in wei
            'is_sufficient': True,
            'symbol': '0x47444f54',
        }

        result = runtime.decode_event_args('AssetRegistry.Updated', args, '302')

        expected_values = {
            'asset_id': 69,
            'asset_name': 'GIGADOT',  # Should be decoded from hex
            'asset_type': 'Erc20',  # Should extract kind from subsquid structure
            'existential_deposit': 1000000000000000000,  # Should be decoded to integer
            'xcm_rate_limit': None,  # Missing optional field
            'symbol': 'GDOT',  # Should be decoded from hex
            'decimals': 18,  # Direct value
            'is_sufficient': True,  # Direct value
        }
        assert result == expected_values
