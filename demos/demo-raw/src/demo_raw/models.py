from tortoise import fields

from dipdup.enums import OperationType
from dipdup.models import Model


class Operation(Model):
    hash = fields.CharField(51)
    level = fields.IntField()
    type = fields.CharEnumField(OperationType)
