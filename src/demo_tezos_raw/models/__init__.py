from dipdup import fields
from dipdup.models import Model
from dipdup.models.tezos import TezosOperationType


class Operation(Model):
    hash = fields.TextField()
    level = fields.IntField()
    type = fields.EnumField(TezosOperationType)
