import logging
from collections import deque
from copy import copy
from typing import Any
from typing import Iterable

from eth_abi.abi import decode as decode_abi
from eth_utils.hexadecimal import decode_hex

from dipdup.config.evm_subsquid_events import SubsquidEventsHandlerConfig
from dipdup.models.evm_subsquid import SubsquidEvent
from dipdup.models.evm_subsquid import SubsquidEventData
from dipdup.package import DipDupPackage
from dipdup.utils import parse_object
from dipdup.utils import pascal_to_snake

_logger = logging.getLogger('dipdup.matcher')


MatchedEventsT = tuple[SubsquidEventsHandlerConfig, SubsquidEvent[Any]]


def prepare_event_handler_args(
    package: DipDupPackage,
    handler_config: SubsquidEventsHandlerConfig,
    matched_event: SubsquidEventData,
) -> SubsquidEvent[Any]:
    """Prepare handler arguments, parse key and value. Schedule callback in executor."""
    _logger.info('%s: `%s` handler matched!', matched_event.level, handler_config.callback)

    typename = handler_config.contract.module_name
    event_abi = package.get_evm_events(typename)[handler_config.name]
    topic1 = decode_hex(matched_event.topics[1] or '')
    topic2 = decode_hex(matched_event.topics[2] or '')

    type_ = package.get_type(
        typename=typename,
        module=f'evm_events.{pascal_to_snake(handler_config.name)}',
        name=handler_config.name,
    )

    byte_data = topic1 + topic2 + decode_hex(matched_event.data)
    data = decode_abi(  # type: ignore[no-untyped-call]
        event_abi['inputs'],
        byte_data,
    )

    typed_payload = parse_object(type_, data, plain=True)
    return SubsquidEvent(
        data=matched_event,
        payload=typed_payload,
    )


def match_event(handler_config: SubsquidEventsHandlerConfig, event: SubsquidEventData, topics: dict[str, str]) -> bool:
    """Match single contract event with pattern"""
    return topics[handler_config.name] == event.topics[0]


def match_events(
    package: DipDupPackage,
    handlers: Iterable[SubsquidEventsHandlerConfig],
    events: Iterable[SubsquidEventData],
) -> deque[MatchedEventsT]:
    """Try to match contract events with all index handlers."""
    matched_handlers: deque[MatchedEventsT] = deque()
    events = deque(events)

    for handler_config in handlers:
        topics = {k: v['topic0'] for k, v in package.get_evm_events(handler_config.contract.module_name).items()}

        # NOTE: Matched events are dropped after processing
        for event in copy(events):
            if not match_event(handler_config, event, topics):
                continue

            arg = prepare_event_handler_args(package, handler_config, event)
            matched_handlers.append((handler_config, arg))

            events.remove(event)

    return matched_handlers
