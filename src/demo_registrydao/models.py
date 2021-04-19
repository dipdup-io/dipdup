from tortoise import Model, fields


class Address(Model):
    address = fields.CharField(36, pk=True)
    balance = fields.IntField()

    class Meta:
        table = 'addresses'


class Proposal(Model):
    id = fields.IntField(pk=True)
    upvotes = fields.IntField(default=0)
    downvotes = fields.IntField(default=0)
    start_date = fields.DatetimeField()
    metadata = fields.JSONField()
    proposer = fields.ForeignKeyField('models.Address', 'proposals')

    class Meta:
        table = 'proposals'


class Vote(Model):
    id = fields.IntField(pk=True)
    proposal = fields.ForeignKeyField('models.Proposal', 'votes')
    amount = fields.IntField()

    class Meta:
        table = 'votes'
