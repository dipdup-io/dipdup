from collections import deque
from copy import copy
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


def decode_event_data(data: str, topics: tuple[str, ...], event_abi: EventAbiExtra) -> Any:
    # FIXME:
    # indexed and non-indexed inputs can go in arbitrary order
    # we need to decode them separately, as:
    #   decode_abi(indexed_inputs, b''.join([decode_hex(topic) for topic in topics[1:]]))
    #   decode_abi(non_indexed_inputs, decode_hex(data))
    # and then merge back
    # that also means we need to store 'indexed' flag together with the types in `EventAbiExtra`
    byte_data = b''.join([decode_hex(topic) for topic in topics[1:]]) + decode_hex(data)
    return decode_abi(
        event_abi.inputs,
        byte_data,
    )


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


def match_event(
    handler_config: SubsquidEventsHandlerConfig,
    event: SubsquidEventData | EvmNodeLogData,
    topics: dict[str, str],
) -> bool:
    """Match single contract event with pattern"""
    return topics[handler_config.name] == event.topics[0]


def match_events(
    package: DipDupPackage,
    handlers: Iterable[SubsquidEventsHandlerConfig],
    events: Iterable[SubsquidEventData | EvmNodeLogData],
) -> deque[MatchedEventsT]:
    """Try to match contract events with all index handlers."""
    matched_handlers: deque[MatchedEventsT] = deque()
    events = deque(events)

    for handler_config in handlers:
        # FIXME: Terribly inefficient; should be cached
        topics = {k: v.topic0 for k, v in package.get_evm_events(handler_config.contract.module_name).items()}
        if not topics:
            continue

        # NOTE: Matched events are dropped after processing
        for event in copy(events):
            if not match_event(handler_config, event, topics):
                continue

            arg = prepare_event_handler_args(package, handler_config, event)
            matched_handlers.append((handler_config, arg))

            events.remove(event)

    return matched_handlers
