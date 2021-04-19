from enum import IntEnum

from tortoise import Model, fields


class TradeSide(IntEnum):
    BUY = 1
    SELL = 0


class Trader(Model):
    address = fields.CharField(36, pk=True)


class Instrument(Model):
    symbol = fields.CharField(max_length=5)


class Trade(Model):
    id = fields.IntField(pk=True)
    instrument = fields.ForeignKeyField('models.Instrument', 'trades')
    trader = fields.ForeignKeyField('models.Trader', 'trades')
    side = fields.IntEnumField(enum_type=TradeSide)
    quantity = fields.DecimalField(decimal_places=6, max_digits=10)
    price = fields.DecimalField(decimal_places=6, max_digits=10)
    slippage = fields.DecimalField(decimal_places=6, max_digits=10)
    level = fields.BigIntField()
    timestamp = fields.DatetimeField()


class Position(Model):
    id = fields.IntField(pk=True)
    instrument = fields.ForeignKeyField('models.Instrument', 'positions')
    trader = fields.ForeignKeyField('models.Trader', 'positions')
    token_qty = fields.DecimalField(decimal_places=6, max_digits=10, default=0)
    tez_qty = fields.DecimalField(decimal_places=6, max_digits=10, default=0)
