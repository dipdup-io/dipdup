import logging
from collections import deque
from collections.abc import Iterable
from contextlib import suppress
from copy import copy
from typing import Any

from dipdup.codegen.tezos_tzkt import get_event_payload_type
from dipdup.config.tezos_tzkt_events import TezosTzktEventsHandlerConfig
from dipdup.config.tezos_tzkt_events import TezosTzktEventsHandlerConfigU
from dipdup.config.tezos_tzkt_events import TezosTzktEventsUnknownEventHandlerConfig
from dipdup.exceptions import FrameworkException
from dipdup.exceptions import InvalidDataError
from dipdup.models.tezos_tzkt import TezosTzktEvent
from dipdup.models.tezos_tzkt import TezosTzktEventData
from dipdup.models.tezos_tzkt import TezosTzktUnknownEvent
from dipdup.package import DipDupPackage
from dipdup.utils import parse_object

_logger = logging.getLogger('dipdup.matcher')


MatchedEventsT = (
    tuple[TezosTzktEventsHandlerConfig, TezosTzktEvent[Any]]
    | tuple[TezosTzktEventsUnknownEventHandlerConfig, TezosTzktUnknownEvent]
)


def prepare_event_handler_args(
    package: DipDupPackage,
    handler_config: TezosTzktEventsHandlerConfigU,
    matched_event: TezosTzktEventData,
) -> TezosTzktEvent[Any] | TezosTzktUnknownEvent | None:
    _logger.debug('%s: `%s` handler matched!', matched_event.level, handler_config.callback)

    if isinstance(handler_config, TezosTzktEventsUnknownEventHandlerConfig):
        return TezosTzktUnknownEvent(
            data=matched_event,
            payload=matched_event.payload,
        )

    type_ = get_event_payload_type(
        package=package,
        typename=handler_config.contract.module_name,
        tag=handler_config.tag,
    )
    if not matched_event.payload:
        raise FrameworkException('Event is typed, but payload is empty')

    with suppress(InvalidDataError):
        typed_payload = parse_object(type_, matched_event.payload)
        return TezosTzktEvent(
            data=matched_event,
            payload=typed_payload,
        )

    return None


def match_event(handler_config: TezosTzktEventsHandlerConfigU, event: TezosTzktEventData) -> bool:
    """Match single contract event with pattern"""
    if isinstance(handler_config, TezosTzktEventsHandlerConfig) and handler_config.tag != event.tag:
        return False
    if handler_config.contract.address != event.contract_address:
        return False
    return True


def match_events(
    package: DipDupPackage,
    handlers: Iterable[TezosTzktEventsHandlerConfigU],
    events: Iterable[TezosTzktEventData],
) -> deque[MatchedEventsT]:
    """Try to match contract events with all index handlers."""
    matched_handlers: deque[MatchedEventsT] = deque()
    events = deque(events)

    for handler_config in handlers:
        # NOTE: Matched events are dropped after processing
        for event in copy(events):
            if not match_event(handler_config, event):
                continue

            arg = prepare_event_handler_args(package, handler_config, event)
            if isinstance(arg, TezosTzktEvent) and isinstance(handler_config, TezosTzktEventsHandlerConfig):
                matched_handlers.append((handler_config, arg))
            elif isinstance(arg, TezosTzktUnknownEvent) and isinstance(
                handler_config, TezosTzktEventsUnknownEventHandlerConfig
            ):
                matched_handlers.append((handler_config, arg))
            elif arg is None:
                continue
            else:
                raise FrameworkException(f'Unexpected handler config type: {type(handler_config)}')

            events.remove(event)

    # NOTE: We don't care about `merge_subscriptions` here implying that all events will be processed
    # NOTE: Maybe "unfiltered" indexes will cover that case?
    for address in {event.contract_address for event in events}:
        _logger.warning('Some events were not matched; fallback handler is missing for `%s`', address)

    return matched_handlers
