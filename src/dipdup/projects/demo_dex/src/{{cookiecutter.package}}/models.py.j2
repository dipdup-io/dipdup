from enum import IntEnum

from tortoise import fields

from dipdup.models import Model


class TradeSide(IntEnum):
    BUY = 1
    SELL = 0


class Trade(Model):
    id = fields.IntField(pk=True)
    symbol = fields.CharField(max_length=5)
    trader = fields.CharField(36)
    side = fields.IntEnumField(enum_type=TradeSide)
    quantity = fields.DecimalField(decimal_places=6, max_digits=20)
    price = fields.DecimalField(decimal_places=6, max_digits=20)
    slippage = fields.DecimalField(decimal_places=6, max_digits=20)
    level = fields.BigIntField()
    timestamp = fields.DatetimeField()


class Position(Model):
    id = fields.IntField(pk=True)
    symbol = fields.CharField(max_length=5)
    trader = fields.CharField(36)
    shares_qty = fields.BigIntField(default=0)
    avg_share_px = fields.DecimalField(decimal_places=6, max_digits=20, default=0)
    realized_pl = fields.DecimalField(decimal_places=6, max_digits=20, default=0)
