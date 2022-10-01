from tortoise import ForeignKeyFieldInstance
from tortoise import fields

from dipdup.models import Model


class DAO(Model):
    address = fields.CharField(36, pk=True)


class Address(Model):
    address = fields.CharField(36, pk=True)
    balance = fields.IntField()

    class Meta:
        table = 'addresses'


class Proposal(Model):
    id = fields.IntField(pk=True)
    dao: ForeignKeyFieldInstance[DAO] = fields.ForeignKeyField('models.DAO', 'proposals')
    # upvotes = fields.IntField(default=0)
    # downvotes = fields.IntField(default=0)
    # start_date = fields.DatetimeField()
    # metadata = fields.JSONField()
    # proposer = fields.ForeignKeyField('models.Address', 'proposals')

    class Meta:
        table = 'proposals'


class Vote(Model):
    id = fields.IntField(pk=True)
    proposal: ForeignKeyFieldInstance[Proposal] = fields.ForeignKeyField('models.Proposal', 'votes')
    amount = fields.IntField()

    class Meta:
        table = 'votes'