from collections.abc import Callable
from typing import TYPE_CHECKING

from dipdup import models
from dipdup.context import DipDupContext

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

_mcp: 'FastMCP | None' = None
_ctx: DipDupContext | None = None


async def _tool_config() -> str:
    assert _ctx
    # FIXME: strip secrets
    return _ctx.config.dump()


async def _tool_indexes() -> str:
    res = ''
    for m in await models.Index.all():
        res += f"""
Index name: {m.name}
Type: {m.type}
Status: {m.status}
Current height: {m.level}
"""
    return res


async def _tool_heads() -> str:
    res = ''
    for m in await models.Head.all():
        res += f"""
Datasource name: {m.name}
Current height: {m.level}
Block hash: {m.hash}
Block timestamp: {m.timestamp}
"""

    return res


def _create_mcp() -> 'FastMCP':
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        'DipDup',
        # FIXME: both not working
        debug=True,
        log_level='DEBUG',
    )

    # NOTE: Internal tools

    mcp.tool(
        name='Config',
        description='Describe the current configuration',
    )(_tool_config)

    mcp.tool(
        name='Indexes',
        description='Fetch the current state of the indexer',
    )(_tool_indexes)

    mcp.tool(
        name='Heads',
        description='Fetch the current datasource head blocks',
    )(_tool_heads)

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


def tool(name: str, description: str) -> Callable[..., None]:
    assert ' ' not in name, 'Tool name should not contain spaces'
    return get_mcp().tool(name=name, description=description)
