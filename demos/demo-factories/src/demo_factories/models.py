from tortoise import fields

from dipdup.models import Model


class Transfer(Model):
    id = fields.IntField(pk=True)
    from_ = fields.TextField()


class Tx(Model):
    id = fields.IntField(pk=True)
    to_ = fields.TextField()
    amount = fields.TextField()
    from_: fields.ForeignKeyRelation['Transfer'] = fields.ForeignKeyField('models.Transfer', related_name='to_')
    from_id: int
