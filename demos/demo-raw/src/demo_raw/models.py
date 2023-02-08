from tortoise import fields

from dipdup.models import Model
from dipdup.models.tezos_tzkt import TzktOperationType


class Operation(Model):
    hash = fields.CharField(51)
    level = fields.IntField()
    type = fields.CharEnumField(TzktOperationType)
