from demo_evm_events import models
from dipdup import mcp


@mcp.tool('TopHolders', 'Get top token holders')
async def tool_holders() -> str:
    holders = await models.Holder.filter().order_by('-balance').limit(10).all()

    res = 'Top token holders by balance:\n\n'
    for i, holder in enumerate(holders):
        res += f'{i}. Address: {holder.address}\n   Balance: {holder.balance}\n'

    return res
