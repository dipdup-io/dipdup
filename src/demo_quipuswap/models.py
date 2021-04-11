from enum import IntEnum

from tortoise import Model, fields


class TradeSide(IntEnum):
    BUY = 0
    SELL = 0


class Trader(Model):
    address = fields.CharField(58, pk=True)


class Trade(Model):
    id = fields.IntField(pk=True)
    symbol = fields.CharField(max_length=5)
    trader = fields.ForeignKeyField('models.Trader', 'trades')
    level = fields.BigIntField()
    timestamp = fields.DatetimeField()
    side = fields.IntEnumField(enum_type=TradeSide)
    qty = fields.DecimalField(decimal_places=6, max_digits=10)
    px = fields.DecimalField(decimal_places=6, max_digits=10)
    slippage = fields.DecimalField(decimal_places=6, max_digits=10)


class Position(Model):
    id = fields.IntField(pk=True)
    symbol = fields.CharField(max_length=5)
    trader = fields.ForeignKeyField('models.Trader', 'positions')
    token_qty = fields.DecimalField(decimal_places=6, max_digits=10)
    tez_qty = fields.DecimalField(decimal_places=6, max_digits=10)
