from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import Mock

import pytest

from dipdup.exceptions import FrameworkException
from dipdup.runtimes import SubstrateRuntime
from dipdup.runtimes import extract_multilocation_payload
from dipdup.runtimes import extract_subsquid_payload


@contextmanager
def mock_runtime_dependencies() -> Generator[tuple[Mock, Mock, Mock], None, None]:
    """Context manager to mock runtime dependencies and restore them after use."""
    from dipdup import runtimes

    original_get_event_arg_names = runtimes.get_event_arg_names
    runtime_config_mock = Mock()
    scale_obj_mock = Mock()

    try:
        yield runtime_config_mock, scale_obj_mock, runtimes  # type: ignore[misc]
    finally:
        runtimes.get_event_arg_names = original_get_event_arg_names


def create_test_runtime() -> SubstrateRuntime:
    """Create a test SubstrateRuntime instance with mocked dependencies."""
    config = Mock()
    package = Mock()
    interface = None
    return SubstrateRuntime(config, package, interface)


def setup_runtime_mocks(
    runtime: SubstrateRuntime, event_abi: dict[str, Any], arg_names: tuple[str, ...], scale_process_return: Any = None
) -> tuple[Mock, Mock]:
    """Setup common mocks for SubstrateRuntime testing."""
    # Mock spec version and event ABI
    spec_version_mock = Mock()
    spec_version_mock.get_event_abi.return_value = event_abi
    runtime.get_spec_version = Mock(return_value=spec_version_mock)  # type: ignore[method-assign]

    # Mock runtime config for parsing
    runtime_config_mock = Mock()
    scale_obj_mock = Mock()

    if scale_process_return is not None:
        scale_obj_mock.process.return_value = scale_process_return

    runtime_config_mock.create_scale_object.return_value = scale_obj_mock
    runtime.runtime_config = runtime_config_mock

    return runtime_config_mock, scale_obj_mock


def assert_result_contains_fields(result: dict[str, Any], expected_fields: list[str]) -> None:
    """Assert that result contains all expected fields."""
    for field in expected_fields:
        assert field in result, f"Field '{field}' missing from result"


def assert_field_values(result: dict[str, Any], expected_values: dict[str, Any]) -> None:
    """Assert that result fields have expected values."""
    for field, expected_value in expected_values.items():
        assert result[field] == expected_value, f"Field '{field}' has value {result[field]}, expected {expected_value}"


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


class TestSubstrateRuntimeDecodeEventArgs:
    """Test cases for SubstrateRuntime.decode_event_args method."""

    def test_decode_event_args_with_camelcase_dict_and_optionals(self) -> None:
        """Test decoding event args with camelCase keys and optional fields."""
        runtime = create_test_runtime()

        event_abi = {
            'args': [
                'U32',
                'option<bounded_collections:bounded_vec:BoundedVec@194>',
                'pallet_asset_registry:types:AssetType',
                'U128',
                'option<U128>',
                'option<bounded_collections:bounded_vec:BoundedVec@194>',
                'option<U8>',
                'Bool',
            ]
        }

        arg_names = (
            'asset_id',
            'asset_name',
            'asset_type',
            'existential_deposit',
            'xcm_rate_limit',
            'symbol',
            'decimals',
            'is_sufficient',
        )

        with mock_runtime_dependencies() as (runtime_config_mock, scale_obj_mock, runtimes):
            # Setup mocks
            setup_runtime_mocks(runtime, event_abi, arg_names, {'__kind': 'External'})
            runtimes.get_event_arg_names = Mock(return_value=arg_names)
            scale_obj_mock.process.return_value = {'__kind': 'External'}

            # Input args with camelCase keys and missing optional fields
            args = {
                'assetId': 1000915,
                'assetType': {'__kind': 'External'},
                'existentialDeposit': '1',
                'isSufficient': False,
            }

            result = runtime.decode_event_args('test.Event', args, '1000')

            # Verify the result contains all expected fields
            expected_fields = [
                'asset_id',
                'asset_name',
                'asset_type',
                'existential_deposit',
                'xcm_rate_limit',
                'symbol',
                'decimals',
                'is_sufficient',
            ]
            assert_result_contains_fields(result, expected_fields)

            # Verify values are correctly mapped
            expected_values = {
                'asset_id': 1000915,
                'asset_name': None,
                'asset_type': 'External',
                'existential_deposit': 1,
                'xcm_rate_limit': None,
                'symbol': None,
                'decimals': None,
                'is_sufficient': False,
            }
            assert_field_values(result, expected_values)

    def test_decode_event_args_missing_required_field(self) -> None:
        """Test that missing required fields raise FrameworkException."""
        runtime = create_test_runtime()

        event_abi = {'args': ['U32', 'Bool']}  # Two required fields
        arg_names = ('asset_id', 'is_required')

        with mock_runtime_dependencies() as (runtime_config_mock, scale_obj_mock, runtimes):
            setup_runtime_mocks(runtime, event_abi, arg_names)
            runtimes.get_event_arg_names = Mock(return_value=arg_names)

            # Input args missing a required field
            args = {
                'assetId': 1000915,
                # Missing "isRequired" field
            }

            with pytest.raises(FrameworkException, match='Required argument `is_required` not found in args'):
                runtime.decode_event_args('test.Event', args, '1000')

    def test_decode_event_args_with_list_input(self) -> None:
        """Test decoding event args when input is a list."""
        runtime = create_test_runtime()

        event_abi = {'args': ['U32', 'option<U128>', 'Bool']}
        arg_names = ('asset_id', 'optional_field', 'is_active')

        with mock_runtime_dependencies() as (runtime_config_mock, scale_obj_mock, runtimes):
            setup_runtime_mocks(runtime, event_abi, arg_names)
            runtimes.get_event_arg_names = Mock(return_value=arg_names)
            scale_obj_mock.process.side_effect = [1000915, True]  # Return values for non-None fields

            # Input args as list - should handle optionals correctly
            args = [1000915, True]  # Missing the optional field in the middle

            result = runtime.decode_event_args('test.Event', args, '1000')

            # Verify the result contains all expected fields
            expected_fields = ['asset_id', 'optional_field', 'is_active']
            assert_result_contains_fields(result, expected_fields)

            # Verify values are correctly mapped
            expected_values = {
                'asset_id': 1000915,
                'optional_field': None,  # Should be None for optional
                'is_active': True,
            }
            assert_field_values(result, expected_values)

    def test_decode_event_args_assets_updated_event(self) -> None:
        """Test decoding event args for Assets.Updated event with specific real-world data."""
        runtime = create_test_runtime()

        event_abi = {
            'args': [
                'U32',
                'option<bounded_collections:bounded_vec:BoundedVec@194>',
                'pallet_asset_registry:types:AssetType',
                'U128',
                'option<U128>',
                'option<bounded_collections:bounded_vec:BoundedVec@194>',
                'option<U8>',
                'Bool',
            ],
            'args_name': [
                'asset_id',
                'asset_name',
                'asset_type',
                'existential_deposit',
                'xcm_rate_limit',
                'symbol',
                'decimals',
                'is_sufficient',
            ],
            'args_type_name': [
                'AssetId',
                'Option<BoundedVec<u8, StringLimit>>',
                'AssetType',
                'Balance',
                'Option<Balance>',
                'Option<BoundedVec<u8, StringLimit>>',
                'Option<u8>',
                'bool',
            ],
            'docs': [],
            'lookup': '3302',
            'name': 'Updated',
        }

        arg_names = (
            'asset_id',
            'asset_name',
            'asset_type',
            'existential_deposit',
            'xcm_rate_limit',
            'symbol',
            'decimals',
            'is_sufficient',
        )

        with mock_runtime_dependencies() as (runtime_config_mock, scale_obj_mock, runtimes):
            # Setup mocks with specific return values for this test case
            _, scale_obj_mock_actual = setup_runtime_mocks(runtime, event_abi, arg_names)
            runtimes.get_event_arg_names = Mock(return_value=arg_names)

            # Create a mapping of expected decoded values
            decode_mapping = {
                '0x47494741444f54': 'GIGADOT',  # asset_name hex to string
                '0x47444f54': 'GDOT',  # symbol hex to string
                '1000000000000000000': 1000000000000000000,  # existential_deposit
            }

            # Configure scale object to return decoded values based on input
            def mock_create_scale_object(type_string, data):  # type: ignore[no-untyped-def]
                mock_scale_obj = Mock()
                data_str = str(data)

                # Check if this data matches any of our expected hex values
                for hex_input, decoded_output in decode_mapping.items():
                    if hex_input in data_str:
                        mock_scale_obj.process.return_value = decoded_output
                        return mock_scale_obj

                # Default case - just return the string representation
                mock_scale_obj.process.return_value = data_str
                return mock_scale_obj

            # Mock the runtime config's create_scale_object method
            runtime.runtime_config.create_scale_object.side_effect = mock_create_scale_object

            # Real args data from the user
            args = {
                'asset_id': 69,
                'asset_name': '0x47494741444f54',
                'asset_type': {'__kind': 'Erc20'},
                'decimals': 18,
                'existential_deposit': '1000000000000000000',  # 1 token in wei
                'is_sufficient': True,
                'symbol': '0x47444f54',
            }

            result = runtime.decode_event_args('Assets.Updated', args, '1000')

            # Verify the result contains all expected fields
            expected_fields = [
                'asset_id',
                'asset_name',
                'asset_type',
                'existential_deposit',
                'xcm_rate_limit',
                'symbol',
                'decimals',
                'is_sufficient',
            ]
            assert_result_contains_fields(result, expected_fields)

            # Verify field values are correctly processed
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
            assert_field_values(result, expected_values)
