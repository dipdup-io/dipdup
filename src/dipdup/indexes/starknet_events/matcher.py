import logging
from collections import deque
from collections.abc import Iterable
from typing import Any

from dipdup.config.starknet_events import StarknetEventsHandlerConfig
from dipdup.models.starknet import StarknetEvent
from dipdup.models.starknet import StarknetEventData
from dipdup.package import DipDupPackage

_logger = logging.getLogger(__name__)

MatchedEventsT = tuple[StarknetEventsHandlerConfig, StarknetEvent[Any]]


def match_events(
    package: DipDupPackage,
    handlers: Iterable[StarknetEventsHandlerConfig],
    events: Iterable[StarknetEventData],
) -> deque[MatchedEventsT]:
    """Try to match event events with all index handlers."""
    matched_handlers: deque[MatchedEventsT] = deque()

    for event in events:
        if not event.keys:
            continue

        for handler_config in handlers:
            name = handler_config.name
            # TODO: store cached event name or match from key0?
            if name != event.keys[0]:
                continue

            address = handler_config.contract.address
            if address and address != event.from_address:
                continue

            arg = prepare_event_handler_args(package, handler_config, event)
            matched_handlers.append((handler_config, arg))
            break

    _logger.debug('%d handlers matched', len(matched_handlers))
    return matched_handlers


def prepare_event_handler_args(*args, **kwargs) -> StarknetEvent[Any]:  # type: ignore[no-untyped-def]
    # TODO: construct event
    raise NotImplementedError
