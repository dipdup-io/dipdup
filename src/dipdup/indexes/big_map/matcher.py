import logging
from collections import deque
from typing import Any
from typing import Iterable

from dipdup.config import BigMapHandlerConfig
from dipdup.models import BigMapData
from dipdup.models import BigMapDiff
from dipdup.utils.codegen import parse_object

_logger = logging.getLogger('dipdup.matcher')

MatchedBigMapsT = tuple[BigMapHandlerConfig, BigMapDiff[Any, Any]]


def prepare_big_map_handler_args(
    handler_config: BigMapHandlerConfig,
    matched_big_map: BigMapData,
) -> BigMapDiff[Any, Any]:
    """Prepare handler arguments, parse key and value. Schedule callback in executor."""
    _logger.info('%s: `%s` handler matched!', matched_big_map.operation_id, handler_config.callback)

    if matched_big_map.action.has_key:
        type_ = handler_config.key_type_cls
        key = parse_object(type_, matched_big_map.key) if type_ else None
    else:
        key = None

    if matched_big_map.action.has_value:
        type_ = handler_config.value_type_cls
        value = parse_object(type_, matched_big_map.value) if type_ else None
    else:
        value = None

    return BigMapDiff(
        data=matched_big_map,
        action=matched_big_map.action,
        key=key,
        value=value,
    )


def match_big_map(
    handler_config: BigMapHandlerConfig,
    big_map: BigMapData,
) -> bool:
    """Match single big map diff with pattern"""
    if handler_config.path != big_map.path:
        return False
    if handler_config.contract.address != big_map.contract_address:
        return False
    return True


def match_big_maps(
    handlers: Iterable[BigMapHandlerConfig],
    big_maps: Iterable[BigMapData],
) -> deque[MatchedBigMapsT]:
    """Try to match big map diffs with all index handlers."""
    matched_handlers: deque[MatchedBigMapsT] = deque()

    for handler_config in handlers:
        for big_map in big_maps:
            big_map_matched = match_big_map(handler_config, big_map)
            if big_map_matched:
                arg = prepare_big_map_handler_args(handler_config, big_map)
                matched_handlers.append((handler_config, arg))

    return matched_handlers
