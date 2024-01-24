from dipdup import fields
from dipdup.models import Model
from dipdup.models.tezos_tzkt import TzktOperationType


class Operation(Model):
    hash = fields.TextField()
    level = fields.IntField()
    type = fields.EnumField(TzktOperationType)