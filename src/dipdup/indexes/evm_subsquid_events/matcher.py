from collections import deque
from copy import copy
from functools import lru_cache
from typing import Any
from typing import Iterable

from eth_abi.abi import decode as decode_abi
from eth_utils.hexadecimal import decode_hex

from dipdup.config.evm_subsquid_events import SubsquidEventsHandlerConfig
from dipdup.models.evm_node import EvmNodeLogData
from dipdup.models.evm_subsquid import SubsquidEvent
from dipdup.models.evm_subsquid import SubsquidEventData
from dipdup.package import DipDupPackage
from dipdup.package import EventAbiExtra
from dipdup.utils import parse_object
from dipdup.utils import pascal_to_snake

MatchedEventsT = tuple[SubsquidEventsHandlerConfig, SubsquidEvent[Any]]


@lru_cache(maxsize=2 ^ 16)
def decode_indexed_topics(indexed_inputs: tuple[str, ...], topics: tuple[str, ...]) -> tuple[Any, ...]:
    indexed_bytes = b''.join(decode_hex(topic) for topic in topics[1:])
    return tuple(decode_abi(indexed_inputs, indexed_bytes))


def decode_event_data(data: str, topics: tuple[str, ...], event_abi: EventAbiExtra) -> tuple[Any, ...]:
    """Decode event data from hex string"""
    # NOTE: Indexed and non-indexed inputs can go in arbitrary order. We need
    # NOTE: to decode them separately and then merge back.
    inputs = event_abi.inputs
    indexed_values = iter(decode_indexed_topics(tuple(n for n, i in inputs if i), topics))

    non_indexed_bytes = decode_hex(data)
    non_indexed_values = iter(decode_abi(tuple(n for n, i in inputs if not i), non_indexed_bytes))

    values: deque[Any] = deque()
    for _, indexed in inputs:
        if indexed:
            values.append(next(indexed_values))
        else:
            values.append(next(non_indexed_values))
    return tuple(values)


def prepare_event_handler_args(
    package: DipDupPackage,
    handler_config: SubsquidEventsHandlerConfig,
    matched_event: SubsquidEventData | EvmNodeLogData,
) -> SubsquidEvent[Any]:
    """Prepare handler arguments, parse key and value. Schedule callback in executor."""

    typename = handler_config.contract.module_name
    event_abi = package.get_evm_events(typename)[handler_config.name]

    type_ = package.get_type(
        typename=typename,
        module=f'evm_events.{pascal_to_snake(handler_config.name)}',
        name=handler_config.name,
    )

    data = decode_event_data(
        data=matched_event.data,
        topics=tuple(matched_event.topics),
        event_abi=event_abi,
    )

    typed_payload = parse_object(
        type_=type_,
        data=data,
        plain=True,
    )
    return SubsquidEvent(
        data=matched_event,
        payload=typed_payload,
    )


def match_events(
    package: DipDupPackage,
    handlers: Iterable[SubsquidEventsHandlerConfig],
    events: Iterable[SubsquidEventData | EvmNodeLogData],
    topics: dict[str, dict[str, str]],
) -> deque[MatchedEventsT]:
    """Try to match contract events with all index handlers."""
    matched_handlers: deque[MatchedEventsT] = deque()
    events = deque(events)

    for handler_config in handlers:
        # NOTE: Matched events are dropped after processing
        for event in copy(events):
            if topics[handler_config.contract.module_name][handler_config.name] != event.topics[0]:
                continue

            arg = prepare_event_handler_args(package, handler_config, event)
            matched_handlers.append((handler_config, arg))

            events.remove(event)

    return matched_handlers
