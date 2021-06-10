from enum import IntEnum

from tortoise import Model, fields


class SwapStatus(IntEnum):
    ACTIVE = 0
    FINISHED = 1
    CANCELED = 2


class Holder(Model):
    address = fields.CharField(36, pk=True)


class Token(Model):
    id = fields.BigIntField(pk=True)
    creator = fields.ForeignKeyField('models.Holder', 'tokens')
    supply = fields.BigIntField()
    level = fields.BigIntField()
    timestamp = fields.DatetimeField()


class Swap(Model):
    id = fields.BigIntField(pk=True)
    creator = fields.ForeignKeyField('models.Holder', 'swaps')
    price = fields.BigIntField()
    amount = fields.BigIntField()
    amount_left = fields.BigIntField()
    level = fields.BigIntField()
    status = fields.IntEnumField(SwapStatus)
    timestamp = fields.DatetimeField()


class Trade(Model):
    id = fields.BigIntField(pk=True)
    swap = fields.ForeignKeyField('models.Swap', 'trades')
    seller = fields.ForeignKeyField('models.Holder', 'sales')
    buyer = fields.ForeignKeyField('models.Holder', 'purchases')
    amount = fields.BigIntField()
    level = fields.BigIntField()
    timestamp = fields.DatetimeField()
