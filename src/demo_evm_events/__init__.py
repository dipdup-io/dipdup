from dipdup import mcp

from demo_evm_events import models


@mcp.tool('TopHolders', 'Top holders stats')
async def tool_holders() -> str:
    holders = await models.Holder.filter().order_by('-balance').limit(10).all()
    res = 'Top holders:\n'
    for holder in holders:
        res += f'{holder.address}: {holder.balance}\n'
    return res
