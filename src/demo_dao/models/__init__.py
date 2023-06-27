
from dipdup import fields
from dipdup.models import Model


class DAO(Model):
    address = fields.TextField(pk=True)


class User(Model):
    address = fields.TextField(pk=True)
    balance = fields.IntField()


class Proposal(Model):
    id = fields.IntField(pk=True)
    dao: fields.ForeignKeyField[DAO] = fields.ForeignKeyField('models.DAO', 'proposals')
    # upvotes = fields.IntField(default=0)
    # downvotes = fields.IntField(default=0)
    # start_date = fields.DatetimeField()
    # metadata = fields.JSONField()
    # proposer = fields.ForeignKeyField('models.Address', 'proposals')


class Vote(Model):
    id = fields.IntField(pk=True)
    proposal: fields.ForeignKeyField[Proposal] = fields.ForeignKeyField('models.Proposal', 'votes')
    amount = fields.IntField()