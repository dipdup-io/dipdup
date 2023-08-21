import logging
from collections import deque
from collections.abc import Iterable
from typing import TYPE_CHECKING
from typing import Any

from dipdup.codegen.tezos_tzkt import get_big_map_key_type
from dipdup.codegen.tezos_tzkt import get_big_map_value_type
from dipdup.config.tezos_tzkt_big_maps import TzktBigMapsHandlerConfig
from dipdup.models.tezos_tzkt import TzktBigMapData
from dipdup.models.tezos_tzkt import TzktBigMapDiff
from dipdup.package import DipDupPackage
from dipdup.utils import parse_object

if TYPE_CHECKING:
    from pydantic import BaseModel

_logger = logging.getLogger('dipdup.matcher')

MatchedBigMapsT = tuple[TzktBigMapsHandlerConfig, TzktBigMapDiff[Any, Any]]


def prepare_big_map_handler_args(
    package: DipDupPackage,
    handler_config: TzktBigMapsHandlerConfig,
    matched_big_map: TzktBigMapData,
) -> TzktBigMapDiff[Any, Any]:
    """Prepare handler arguments, parse key and value. Schedule callback in executor."""
    _logger.debug('%s: `%s` handler matched!', matched_big_map.operation_id, handler_config.callback)

    key: BaseModel | None = None
    value: BaseModel | None = None

    if matched_big_map.action.has_key and matched_big_map.key is not None:
        type_ = get_big_map_key_type(package, handler_config.contract.module_name, handler_config.path)
        key = parse_object(type_, matched_big_map.key) if type_ else None

    if matched_big_map.action.has_value and matched_big_map.value is not None:
        type_ = get_big_map_value_type(package, handler_config.contract.module_name, handler_config.path)
        value = parse_object(type_, matched_big_map.value) if type_ else None

    return TzktBigMapDiff(
        data=matched_big_map,
        action=matched_big_map.action,
        key=key,
        value=value,
    )


def match_big_map(
    handler_config: TzktBigMapsHandlerConfig,
    big_map: TzktBigMapData,
) -> bool:
    """Match single big map diff with pattern"""
    if handler_config.path != big_map.path:
        return False
    if handler_config.contract.address != big_map.contract_address:
        return False
    return True


def match_big_maps(
    package: DipDupPackage,
    handlers: Iterable[TzktBigMapsHandlerConfig],
    big_maps: Iterable[TzktBigMapData],
) -> deque[MatchedBigMapsT]:
    """Try to match big map diffs with all index handlers."""
    matched_handlers: deque[MatchedBigMapsT] = deque()

    for handler_config in handlers:
        for big_map in big_maps:
            big_map_matched = match_big_map(handler_config, big_map)
            if big_map_matched:
                arg = prepare_big_map_handler_args(package, handler_config, big_map)
                matched_handlers.append((handler_config, arg))

    return matched_handlers
