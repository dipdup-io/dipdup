from datetime import datetime, timedelta
from tortoise.transactions import in_transaction
from tortoise.exceptions import OperationalError


async def update_totals():
    async with in_transaction() as conn:
        try:
            updated_at = await conn.execute_query('SELECT updated_at FROM trade_total LIMIT 1')[0][0]
            if datetime.now() - updated_at < timedelta(seconds=1):
                return
        except OperationalError:
            pass

        try:
            await conn.execute_query('CALL trade_summary()')
        except OperationalError:
            pass
