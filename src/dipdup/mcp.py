from __future__ import annotations

import logging
import traceback
from collections.abc import Awaitable
from collections.abc import Callable
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar
from typing import cast

from pydantic import AnyUrl

T = TypeVar('T', bound=Callable[..., Awaitable[Any]])

from dipdup import models
from dipdup.context import McpContext as McpContext
from dipdup.exceptions import FrameworkException
from dipdup.utils import json_dumps

_logger = logging.getLogger(__name__)


import mcp.server
import mcp.types as types

if TYPE_CHECKING:
    from collections.abc import Iterable


# NOTE: Global context management
_ctx: McpContext | None = None


def get_ctx() -> McpContext:
    global _ctx
    if _ctx is None:
        raise FrameworkException('DipDup MCP context is not initialized')
    return _ctx


def set_ctx(ctx: McpContext) -> None:
    global _ctx
    if _ctx is not None:
        raise FrameworkException('DipDup MCP context is already initialized')
    _ctx = ctx


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


async def _tool_api_config() -> str:
    ctx = get_ctx()
    return await ctx.call_api(
        method='get',
        path='/config',
    )


async def _tool_api_add_contract(
    kind: str,
    name: str,
    address: str | None = None,
    typename: str | None = None,
    code_hash: str | int | None = None,
) -> str:
    ctx = get_ctx()
    return await ctx.call_api(
        method='post',
        path='/add_contract',
        params={
            'kind': kind,
            'name': name,
            'address': address,
            'typename': typename,
            'code_hash': code_hash,
        },
    )


async def _tool_api_add_index(
    name: str,
    template: str,
    values: dict[str, Any],
    first_level: int | None = None,
    last_level: int | None = None,
) -> str:
    ctx = get_ctx()
    return await ctx.call_api(
        method='post',
        path='/add_index',
        params={
            'name': name,
            'template': template,
            'values': values,
            'first_level': first_level,
            'last_level': last_level,
        },
    )


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
    from mcp.shared.exceptions import McpError
    from mcp.types import ErrorData

    if name in _user_tools_fn:
        fn = _user_tools_fn[name]
    elif name in DIPDUP_TOOLS_FN:
        fn = DIPDUP_TOOLS_FN[name]
    else:
        msg = f'Tool `{name}` not found'
        raise FrameworkException(msg)

    try:
        res = await fn(**arguments)
        return [types.TextContent(type='text', text=res)]
    except Exception as e:
        _logger.exception('Error while calling tool `%s`', name)
        raise McpError(
            ErrorData(
                code=-1,
                message=str(e),
                data=''.join(traceback.format_exception(type(e), e, e.__traceback__)),
            )
        ) from e


@server.read_resource()  # type: ignore[no-untyped-call,misc]
async def read_resource(uri: AnyUrl) -> str:
    from mcp.shared.exceptions import McpError
    from mcp.types import ErrorData

    if uri.scheme != 'dipdup':
        raise ValueError(f'Invalid scheme: {uri.scheme}')

    name = uri.host.lstrip('/')  # type: ignore[union-attr]

    if name in _user_resources:
        fn = _user_resources_fn[name]
    elif name in DIPDUP_RESOURCES:
        fn = DIPDUP_RESOURCES_FN[name]
    else:
        msg = f'Resource `{name}` not found'
        raise FrameworkException(msg)

    try:
        res = await fn()

        # FIXME: mimeType is always `text/plain`
        return json_dumps(res, None).decode()
    except Exception as e:
        _logger.exception('Error while calling tool `%s`', name)
        raise McpError(
            ErrorData(
                code=-1,
                message=str(e),
                data=''.join(traceback.format_exception(type(e), e, e.__traceback__)),
            )
        ) from e


def tool(
    name: str,
    description: str,
    namespace: str = 'project',
) -> Callable[[T], T]:
    def wrapper(func: T) -> T:
        nonlocal name
        global _user_tools
        global _user_tools_fn

        name = f'{namespace}_{name}'

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


def resource(name: str, description: str, mime_type: str) -> Callable[[T], T]:
    def wrapper(func: T) -> T:
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


# NOTE: Register built-in tools
tool(
    name='add_contract',
    description='Add a new contract to the running indexer',
    namespace='api',
)(_tool_api_add_contract)
tool(
    name='add_index',
    description='Add a new index to the running indexer',
    namespace='api',
)(_tool_api_add_index)
tool(
    name='config',
    description='Get the current indexer configuration',
    namespace='api',
)(_tool_api_config)


# FIXME: Many clients still don't support resources. Expose them as tools too.
def expose_resources_as_tools() -> None:
    for name, res in DIPDUP_RESOURCES.items():
        desc = f'Compatibility alias for resource `{name}`: {res.description}'

        async def _proxy_resource(name: str = name) -> str:
            res = await DIPDUP_RESOURCES_FN[name]()
            if isinstance(res, str):
                return res
            return json_dumps(res, None).decode()

        tool(name, desc, namespace='resource')(_proxy_resource)
