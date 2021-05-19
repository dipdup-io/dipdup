from enum import IntEnum

from tortoise import Model, fields


class TradeSide(IntEnum):
    BUY = 1
    SELL = 0


class Symbol(Model):
    symbol = fields.CharField(max_length=32, pk=True)


class Trader(Model):
    address = fields.CharField(36, pk=True)
    trades_qty = fields.IntField(default=0)
    trades_amount = fields.DecimalField(10, 6, default=0)


class Trade(Model):
    id = fields.IntField(pk=True)
    symbol = fields.ForeignKeyField('models.Symbol', 'trades')
    trader = fields.ForeignKeyField('models.Trader', 'trades')
    side = fields.IntEnumField(enum_type=TradeSide)
    quantity = fields.DecimalField(decimal_places=6, max_digits=20)
    price = fields.DecimalField(decimal_places=6, max_digits=20)
    slippage = fields.DecimalField(decimal_places=6, max_digits=20)
    level = fields.BigIntField()
    timestamp = fields.DatetimeField()


class Position(Model):
    id = fields.IntField(pk=True)
    symbol = fields.ForeignKeyField('models.Symbol', 'positions')
    trader = fields.ForeignKeyField('models.Trader', 'positions')
    shares_qty = fields.BigIntField(default=0)
    avg_share_px = fields.DecimalField(decimal_places=6, max_digits=20, default=0)
    realized_pl = fields.DecimalField(decimal_places=6, max_digits=20, default=0)
