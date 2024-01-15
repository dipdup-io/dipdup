import logging
from collections import deque
from collections.abc import Iterable
from typing import Any

from eth_abi.abi import decode as decode_abi
from eth_utils.hexadecimal import decode_hex
from web3 import Web3

from dipdup.config.evm_subsquid_transactions import SubsquidTransactionsHandlerConfig
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import FrameworkException
from dipdup.models.evm_node import EvmNodeTransactionData
from dipdup.models.evm_subsquid import SubsquidTransaction
from dipdup.models.evm_subsquid import SubsquidTransactionData
from dipdup.package import DipDupPackage
from dipdup.utils import parse_object
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal

_logger = logging.getLogger(__name__)

MatchedTransactionsT = tuple[
    SubsquidTransactionsHandlerConfig, SubsquidTransaction[Any] | SubsquidTransactionData | EvmNodeTransactionData
]


def prepare_transaction_handler_args(
    package: DipDupPackage,
    handler_config: SubsquidTransactionsHandlerConfig,
    matched_transaction: SubsquidTransactionData | EvmNodeTransactionData,
) -> SubsquidTransaction[Any]:
    method, contract = handler_config.method, handler_config.to
    if not method or not contract:
        raise FrameworkException('`method` and `to` are required for typed transaction handler')
    typename = contract.module_name

    inputs = package.get_converted_abi(typename)['methods'][method]['inputs']
    data = decode_abi(
        types=tuple(input['type'] for input in inputs),
        data=decode_hex(matched_transaction.input[10:]),
    )

    type_ = package.get_type(
        typename=typename,
        module=f'evm_methods.{pascal_to_snake(method)}',
        name=snake_to_pascal(method),
    )
    typed_input = parse_object(
        type_=type_,
        data=data,
        plain=True,
    )
    return SubsquidTransaction(
        data=matched_transaction,
        input=typed_input,
    )


def match_transactions(
    package: DipDupPackage,
    handlers: Iterable[SubsquidTransactionsHandlerConfig],
    transactions: Iterable[SubsquidTransactionData | EvmNodeTransactionData],
) -> deque[MatchedTransactionsT]:
    """Try to match contract transactions with all index handlers."""
    matched_handlers: deque[MatchedTransactionsT] = deque()

    for transaction in transactions:
        for handler_config in handlers:
            if (from_ := handler_config.from_) and from_.address != transaction.from_:
                continue
            if (to := handler_config.to) and to.address != transaction.to:
                continue
            if handler_config.method:
                if to:
                    sighash = package.get_converted_abi(to.module_name)['methods'][handler_config.method]['sighash']
                    if sighash != transaction.sighash:
                        continue
                else:
                    if not {'(', ')'} <= set(handler_config.method):
                        raise ConfigurationError('`to` field is missing, but `method` is not a full signature')
                    sighash = Web3.keccak(text=handler_config.method).hex()[:10]
                    if sighash != transaction.sighash:
                        continue

            arg = (
                prepare_transaction_handler_args(package, handler_config, transaction)
                if handler_config.typed_contract
                else transaction
            )
            matched_handlers.append((handler_config, arg))
            break

    _logger.debug('%d handlers matched', len(matched_handlers))
    return matched_handlers
