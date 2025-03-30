from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from pydantic import AnyUrl

from dipdup import models
from dipdup.context import McpContext
from dipdup.exceptions import FrameworkException
from dipdup.utils import json_dumps

_logger = logging.getLogger(__name__)

_ctx: McpContext | None = None

import mcp.server
import mcp.types as types

if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable
    from collections.abc import Iterable

# NOTE: Resource and tool callbacks


async def _resource_config() -> str:
    return get_ctx().config._json.dump(strip_secrets=True)


async def _resource_metrics() -> dict[str, Any]:
    metrics_model = await models.Meta.get_or_none(key='dipdup_metrics')
    if metrics_model:
        return cast('dict[str, Any]', metrics_model.value)
    return {}


async def _resource_heads() -> list[dict[str, Any]]:
    res = []
    for m in await models.Head.all():
        res.append(
            {
                'datasource_name': m.name,
                'level': m.level,
                'hash': m.hash,
                'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': m.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
        )
    return res


async def _resource_indexes() -> list[dict[str, Any]]:
    res = []
    for m in await models.Index.all():
        res.append(
            {
                'name': m.name,
                'kind': m.type.value,
                'status': m.status.value,
                'height': m.level,
                'updated_at': m.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
        )
    return res


# NOTE: Built-in tools and resources

DIPDUP_RESOURCES: dict[str, types.Resource] = {
    'config': types.Resource(
        uri=AnyUrl('dipdup://config'),
        name='config',
        description='Dump the current indexer configuration in YAML format',
        mimeType='text/plain',
    ),
    'metrics': types.Resource(
        uri=AnyUrl('dipdup://metrics'),
        name='metrics',
        description='Show the current indexer metrics',
        mimeType='application/json',
    ),
    'heads': types.Resource(
        uri=AnyUrl('dipdup://heads'),
        name='heads',
        description='Show the current datasource head blocks',
        mimeType='application/json',
    ),
    'indexes': types.Resource(
        uri=AnyUrl('dipdup://indexes'),
        name='indexes',
        description='Show the current indexer state',
        mimeType='application/json',
    ),
}
DIPDUP_RESOURCES_FN: dict[str, Callable[..., Awaitable[Any]]] = {
    'config': _resource_config,
    'metrics': _resource_metrics,
    'heads': _resource_heads,
    'indexes': _resource_indexes,
}

DIPDUP_TOOLS: dict[str, types.Tool] = {}
DIPDUP_TOOLS_FN: dict[str, Callable[..., Awaitable[Iterable[str]]]] = {}

# NOTE: Context management


def get_ctx() -> McpContext:
    global _ctx
    if _ctx is None:
        raise FrameworkException('DipDup context is not initialized')
    return _ctx


def _set_ctx(ctx: McpContext) -> None:
    global _ctx
    if _ctx is not None:
        raise FrameworkException('DipDup context is already initialized')
    _ctx = ctx


# TODO: Add instructions
server: mcp.server.Server[Any] = mcp.server.Server(name='DipDup')
_user_tools: dict[str, types.Tool] = {}
_user_tools_fn: dict[str, Callable[..., Awaitable[Iterable[str]]]] = {}
_user_resources: dict[str, types.Resource] = {}
_user_resources_fn: dict[str, Callable[..., Awaitable[Iterable[str]]]] = {}


# TODO: Push typehints to upstream
@server.list_tools()  # type: ignore[no-untyped-call,misc]
async def list_tools() -> list[types.Tool]:
    return [
        *list(DIPDUP_TOOLS.values()),
        *list(_user_tools.values()),
    ]


@server.list_resources()  # type: ignore[no-untyped-call,misc]
async def list_resources() -> list[types.Resource]:
    return [
        *list(DIPDUP_RESOURCES.values()),
        *list(_user_resources.values()),
    ]


# FIXME: Not supported
@server.list_resource_templates()  # type: ignore[no-untyped-call,misc]
async def list_resource_templates() -> list[types.ResourceTemplate]:
    return []


@server.call_tool()  # type: ignore[no-untyped-call,misc]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    if name in _user_tools_fn:
        res = await _user_tools_fn[name](**arguments)
        return [types.TextContent(type='text', text=res)]

    if name in DIPDUP_TOOLS_FN:
        res = await DIPDUP_TOOLS_FN[name](**arguments)
        return [types.TextContent(type='text', text=res)]

    raise NotImplementedError(name)


@server.read_resource()  # type: ignore[no-untyped-call,misc]
async def read_resource(uri: AnyUrl) -> str:
    if uri.scheme != 'dipdup':
        raise ValueError(f'Invalid scheme: {uri.scheme}')

    name = uri.host.lstrip('/')  # type: ignore[union-attr]
    if name in _user_resources_fn:
        res = await _user_resources_fn[name]()
    elif name in DIPDUP_RESOURCES_FN:
        res = await DIPDUP_RESOURCES_FN[name]()
    else:
        msg = f'Resource `{name}` not found'
        raise FrameworkException(msg)

    # FIXME: mimeType is always `text/plain`
    return json_dumps(res, None).decode()


def tool(name: str, description: str) -> Any:
    def wrapper(func: Any) -> Any:
        global _user_tools
        global _user_tools_fn

        if name in _user_tools or name in DIPDUP_TOOLS:
            msg = f'Tool `{name}` is already registered'
            raise FrameworkException(msg)

        from mcp.server.fastmcp.tools.base import Tool

        tool_info = Tool.from_function(func, name=name, description=description)

        _user_tools[name] = types.Tool(
            name=name,
            description=description,
            inputSchema=tool_info.parameters,
        )
        _user_tools_fn[name] = func

        return func

    return wrapper


def resource(name: str, description: str, mime_type: str) -> Any:
    def wrapper(func: Any) -> Any:
        global _user_resources
        global _user_resources_fn

        if name in _user_resources or name in DIPDUP_RESOURCES:
            msg = f'Resource `{name}` is already registered'
            raise FrameworkException(msg)

        _user_resources[name] = types.Resource(
            uri=AnyUrl(f'dipdup://{name}'),
            name=name,
            description=description,
            mimeType=mime_type,
        )
        _user_resources_fn[name] = func
        return func

    return wrapper
