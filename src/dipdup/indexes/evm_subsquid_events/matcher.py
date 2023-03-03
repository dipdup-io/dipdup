import logging
from collections import deque
from copy import copy
from typing import Any
from typing import Iterable

from eth_abi import decode as decode_abi
from eth_utils import decode_hex

from dipdup.codegen.evm_subsquid import get_event_log_type
from dipdup.config.evm_subsquid_events import SubsquidEventsHandlerConfig
from dipdup.models.evm_subsquid import SubsquidEvent
from dipdup.models.evm_subsquid import SubsquidEventData
from dipdup.package import DipDupPackage
from dipdup.utils import parse_object

_logger = logging.getLogger('dipdup.matcher')


MatchedEventsT = tuple[SubsquidEventsHandlerConfig, SubsquidEvent[Any]]


def prepare_event_handler_args(
    package: DipDupPackage,
    handler_config: SubsquidEventsHandlerConfig,
    matched_event: SubsquidEventData,
) -> SubsquidEvent[Any]:
    """Prepare handler arguments, parse key and value. Schedule callback in executor."""
    _logger.info('%s: `%s` handler matched!', matched_event.level, handler_config.callback)

    type_ = get_event_log_type(
        package=package,
        typename=handler_config.contract.module_name,
        name=handler_config.name,
    )

    # FIXME: Decoding here
    byte_data = decode_hex(matched_event.data)
    data = decode_abi(
        ['address', 'address', 'uint256'],
        byte_data,
    )

    typed_payload = parse_object(type_, data)
    return SubsquidEvent(
        data=matched_event,
        payload=typed_payload,
    )


def match_event(handler_config: SubsquidEventsHandlerConfig, event: SubsquidEventData, topics: dict[str, str]) -> bool:
    """Match single contract event with pattern"""

    # FIXME: No topic-name mapping here; set on config load
    # if handler_config.topic != event.topic0:
    #     return False
    # if handler_config.contract.address != event.address:
    #     return False
    return True


def match_events(
    package: DipDupPackage,
    handlers: Iterable[SubsquidEventsHandlerConfig],
    events: Iterable[SubsquidEventData],
) -> deque[MatchedEventsT]:
    """Try to match contract events with all index handlers."""
    matched_handlers: deque[MatchedEventsT] = deque()
    events = deque(events)

    for handler_config in handlers:
        # NOTE: Matched events are dropped after processing
        for event in copy(events):
            if not match_event(handler_config, event, {}):
                continue

            arg = prepare_event_handler_args(package, handler_config, event)
            matched_handlers.append((handler_config, arg))

            events.remove(event)

    return matched_handlers
