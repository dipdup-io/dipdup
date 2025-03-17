from collections.abc import Callable
from typing import TYPE_CHECKING
from typing import Any

from dipdup import models
from dipdup.context import DipDupContext

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

_mcp: 'FastMCP | None' = None
_ctx: DipDupContext | None = None


async def _resource_config() -> str:
    assert _ctx
    secret_keys = {'password', 'api_key', 'secret'}
    dump = _ctx.config.dump()
    # TODO: More accurate filtering
    return '\n'.join(
        line if not any(key in line for key in secret_keys) else f'{line.split(":")[0]}: ***'
        for line in '\n'.split(dump)
    )


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


def _create_mcp() -> 'FastMCP':
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        'DipDup',
        # FIXME: both not working
        debug=True,
        log_level='DEBUG',
    )

    # NOTE: Internal tools

    mcp.resource(
        uri='dipdup://config',
        name='Config',
        description='Dump the current indexer configuration in YAML format',
        mime_type='application/yaml',
    )(_resource_config)

    mcp.resource(
        uri='dipdup://metrics',
        name='Metrics',
        description='Show the current indexer metrics',
        mime_type='application/json',
    )(_resource_metrics)

    mcp.resource(
        uri='dipdup://heads',
        name='Heads',
        description='Show the current datasource head blocks',
        mime_type='application/json',
    )(_resource_heads)

    mcp.resource(
        uri='dipdup://indexes',
        name='Indexes',
        description='Show the current indexer state',
        mime_type='application/json',
    )(_resource_indexes)

    return mcp


def configure_mcp(ctx: DipDupContext) -> None:
    global _ctx
    _ctx = ctx

    if mcp_config := ctx.config.mcp:
        mcp = get_mcp()
        mcp.settings.host = mcp_config.host
        mcp.settings.port = mcp_config.port


def get_mcp() -> 'FastMCP':
    global _mcp

    if not _mcp:
        _mcp = _create_mcp()

    return _mcp


def tool(
    name: str,
    description: str,
) -> Callable[..., None]:
    assert ' ' not in name, 'Name should not contain spaces'
    return get_mcp().tool(
        name=name,
        description=description,
    )


def resource(
    self,
    uri: str,
    *,
    name: str | None = None,
    description: str | None = None,
    mime_type: str | None = None,
) -> Callable[..., None]:
    assert ' ' not in name, 'Name should not contain spaces'
    return get_mcp().resource(
        uri,
        name=name,
        description=description,
        mime_type=mime_type,
    )


def prompt(
    self,
    name: str | None = None,
    description: str | None = None,
) -> Callable[..., None]:
    assert ' ' not in name, 'Name should not contain spaces'
    return get_mcp().prompt(
        name=name,
        description=description,
    )
