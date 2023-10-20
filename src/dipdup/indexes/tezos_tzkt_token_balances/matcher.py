import logging
from collections import deque
from collections.abc import Iterable

from dipdup.config.tezos_tzkt_token_balances import TzktTokenBalancesHandlerConfig
from dipdup.models.tezos_tzkt import TzktTokenBalanceData

_logger = logging.getLogger('dipdup.matcher')

MatchedTokenBalancesT = tuple[TzktTokenBalancesHandlerConfig, TzktTokenBalanceData]


def match_token_balance(
    handler_config: TzktTokenBalancesHandlerConfig,
    token_balance: TzktTokenBalanceData,
) -> bool:
    """Match single token balance with pattern"""
    if handler_config.contract:
        if handler_config.contract.address != token_balance.contract_address:
            return False
    if handler_config.token_id is not None:
        if handler_config.token_id != token_balance.token_id:
            return False
    return True


def match_token_balances(
    handlers: Iterable[TzktTokenBalancesHandlerConfig], token_balances: Iterable[TzktTokenBalanceData]
) -> deque[MatchedTokenBalancesT]:
    """Try to match token balances with all index handlers."""

    matched_handlers: deque[MatchedTokenBalancesT] = deque()

    for token_balance in token_balances:
        for handler_config in handlers:
            token_balance_matched = match_token_balance(handler_config, token_balance)
            if not token_balance_matched:
                continue
            _logger.debug('%s: `%s` handler matched!', token_balance.level, handler_config.callback)
            matched_handlers.append((handler_config, token_balance))

    return matched_handlers
