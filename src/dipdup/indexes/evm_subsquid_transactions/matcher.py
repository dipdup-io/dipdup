import logging
from collections import deque
from collections.abc import Iterable
from typing import Any

from web3 import Web3

from dipdup.config.evm_subsquid_transactions import SubsquidTransactionsHandlerConfig
from dipdup.exceptions import ConfigurationError
from dipdup.models.evm_node import EvmNodeTransactionData
from dipdup.models.evm_subsquid import SubsquidTransaction
from dipdup.models.evm_subsquid import SubsquidTransactionData
from dipdup.package import DipDupPackage

_logger = logging.getLogger(__name__)

MatchedTransactionsT = tuple[SubsquidTransactionsHandlerConfig, SubsquidTransaction[Any]]


def match_transactions(
    package: DipDupPackage,
    handlers: Iterable[SubsquidTransactionsHandlerConfig],
    transactions: Iterable[SubsquidTransactionData | EvmNodeTransactionData],
    sighashes: dict[str, str],
) -> deque[MatchedTransactionsT]:
    """Try to match contract transactions with all index handlers."""
    matched_handlers: deque[MatchedTransactionsT] = deque()

    for transaction in transactions:
        for handler_config in handlers:
            if handler_config.from_ not in (transaction.from_, None):
                continue
            if handler_config.to not in (transaction.to, None):
                continue
            if handler_config.method:
                if (
                    handler_config.to
                    and package.get_converted_abi(handler_config.to.module_name)['methods'][handler_config.method][
                        'sighash'
                    ]
                    != transaction.sighash
                ):
                    continue
                if not {'(', ')'} <= set(handler_config.method):
                    raise ConfigurationError('`to` field is missing; `method` is not a sighash')
                sighash = Web3.keccak(text=handler_config.method).hex()[:10]
                if sighash != transaction.sighash:
                    continue

            arg = prepare_transaction_handler_args(package, handler_config, transaction)
            matched_handlers.append((handler_config, arg))
            break

    _logger.debug('%d handlers matched', len(matched_handlers))
    return matched_handlers
