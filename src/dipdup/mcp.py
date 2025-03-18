import logging
from typing import Any

from pydantic import AnyUrl

from dipdup import models
from dipdup.context import DipDupContext
from dipdup.utils import json_dumps

_logger = logging.getLogger(__name__)

_ctx: DipDupContext | None = None

import mcp.server

mcp.server.logger = _logger

import mcp.types as types


def get_ctx() -> DipDupContext:
    global _ctx
    if _ctx is None:
        raise ValueError('DipDup context is not initialized')
    return _ctx


def set_ctx(ctx: DipDupContext):
    global _ctx
    _ctx = ctx


_app: mcp.server.Server = mcp.server.Server(name='DipDup')


@_app.list_tools()  # type: ignore[no-untyped-call,misc]
async def list_tools() -> list[types.Tool]:
    return []
    # return [
    #     types.Tool(
    #         name='config',
    #         description='Dump the current indexer configuration in YAML format',
    #         inputSchema={
    #             'type': 'object',
    #             'properties': {},
    #         },
    #     ),
    #     types.Tool(
    #         name='metrics',
    #         description='Show the current indexer metrics',
    #         inputSchema={
    #             'type': 'object',
    #             'properties': {},
    #         },
    #     ),
    #     types.Tool(
    #         name='heads',
    #         description='Show the current datasource head blocks',
    #         inputSchema={
    #             'type': 'object',
    #             'properties': {},
    #         },
    #     ),
    #     types.Tool(
    #         name='indexes',
    #         description='Show the current indexer state',
    #         inputSchema={
    #             'type': 'object',
    #             'properties': {},
    #         },
    #     ),
    # ]


@_app.list_resources()  # type: ignore[no-untyped-call,misc]
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri=AnyUrl('dipdup://config'),
            name='config',
            description='Dump the current indexer configuration in YAML format',
            mimeType='application/yaml',
        ),
        types.Resource(
            uri=AnyUrl('dipdup://metrics'),
            name='metrics',
            description='Show the current indexer metrics',
            mimeType='application/json',
        ),
        types.Resource(
            uri=AnyUrl('dipdup://heads'),
            name='heads',
            description='Show the current datasource head blocks',
            mimeType='application/json',
        ),
        types.Resource(
            uri=AnyUrl('dipdup://indexes'),
            name='indexes',
            description='Show the current indexer state',
            mimeType='application/json',
        ),
    ]


@_app.call_tool()  # type: ignore[no-untyped-call,misc]
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    # if name == 'config':
    #     return [types.TextContent(type='text', text=str(await _resource_config()))]
    # if name == 'metrics':
    #     return [types.TextContent(type='text', text=str(await _resource_metrics()))]
    # if name == 'heads':
    #     return [types.TextContent(type='text', text=str(await _resource_heads()))]
    # if name == 'indexes':
    #     return [types.TextContent(type='text', text=str(await _resource_indexes()))]
    return []


@_app.read_resource()  # type: ignore[no-untyped-call,misc]
async def read_resource(uri: AnyUrl) -> str:
    uri = str(uri)
    if uri == 'dipdup://config':
        res = await _resource_config()
    elif uri == 'dipdup://metrics':
        res = await _resource_metrics()
    elif uri == 'dipdup://heads':
        res = await _resource_heads()
    elif uri == 'dipdup://indexes':
        res = await _resource_indexes()
    else:
        raise NotImplementedError(uri)

    return json_dumps(res)


async def _resource_config() -> dict[str, Any]:
    assert _ctx
    return _ctx.config._json.dump(strip_secrets=True)


async def _resource_metrics() -> dict[str, Any]:
    metrics_model = await models.Meta.get_or_none(key='dipdup_metrics')
    if metrics_model:
        return metrics_model.value
    return {}


async def _resource_heads() -> list[dict[str, Any]]:
    res = []
    for m in await models.Head.all():
        res.append(
            {
                'datasource_name': m.name,
                'level': m.level,
                'hash': m.hash,
                'timestamp': m.timestamp,
                'updated_at': m.updated_at,
            }
        )
    return res


async def _resource_indexes() -> list[dict[str, Any]]:
    res = []
    for m in await models.Index.all():
        res.append(
            {
                'name': m.name,
                'kind': m.type,
                'status': m.status,
                'height': m.level,
                'updated_at': m.updated_at,
            }
        )
    return res
