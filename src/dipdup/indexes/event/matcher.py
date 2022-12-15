import logging
from collections import deque
from contextlib import suppress
from copy import copy
from typing import Any
from typing import Iterable
from typing import Union

from dipdup.config import EventHandlerConfig
from dipdup.config import EventHandlerConfigU
from dipdup.config import UnknownEventHandlerConfig
from dipdup.exceptions import FrameworkException
from dipdup.exceptions import InvalidDataError
from dipdup.models import Event
from dipdup.models import EventData
from dipdup.models import UnknownEvent
from dipdup.utils.codegen import parse_object

_logger = logging.getLogger('dipdup.matcher')


MatchedEventsT = Union[
    tuple[EventHandlerConfig, Event[Any]],
    tuple[UnknownEventHandlerConfig, UnknownEvent],
]


def prepare_event_handler_args(
    handler_config: EventHandlerConfigU,
    matched_event: EventData,
) -> Event[Any] | UnknownEvent | None:
    """Prepare handler arguments, parse key and value. Schedule callback in executor."""
    _logger.info('%s: `%s` handler matched!', matched_event.level, handler_config.callback)

    if isinstance(handler_config, UnknownEventHandlerConfig):
        return UnknownEvent(
            data=matched_event,
            payload=matched_event.payload,
        )

    with suppress(InvalidDataError):
        type_ = handler_config.event_type_cls
        payload: Event[Any] = parse_object(type_, matched_event.payload)
        return Event(
            data=matched_event,
            payload=payload,
        )

    return None


def match_event(handler_config: EventHandlerConfigU, event: EventData) -> bool:
    """Match single contract event with pattern"""
    if isinstance(handler_config, EventHandlerConfig) and handler_config.tag != event.tag:
        return False
    if handler_config.contract.address != event.contract_address:
        return False
    return True


def match_events(
    handlers: Iterable[EventHandlerConfigU],
    events: Iterable[EventData],
) -> deque[MatchedEventsT]:
    """Try to match contract events with all index handlers."""
    matched_handlers: deque[MatchedEventsT] = deque()
    events = deque(events)

    for handler_config in handlers:
        # NOTE: Matched events are dropped after processing
        for event in copy(events):
            if not match_event(handler_config, event):
                continue

            arg = prepare_event_handler_args(handler_config, event)
            if isinstance(arg, Event) and isinstance(handler_config, EventHandlerConfig):
                matched_handlers.append((handler_config, arg))
            elif isinstance(arg, UnknownEvent) and isinstance(handler_config, UnknownEventHandlerConfig):
                matched_handlers.append((handler_config, arg))
            elif arg is None:
                continue
            else:
                raise FrameworkException(f'Unexpected handler config type: {type(handler_config)}')

            events.remove(event)

    # NOTE: We don't care about `merge_subscriptions` here implying that all events will be processed
    # NOTE: Maybe "unfiltered" indexes will cover that case?
    for address in {event.contract_address for event in events}:
        _logger.warning('Some events were not matched; fallback handler is missing for `{}`', address)

    return matched_handlers
