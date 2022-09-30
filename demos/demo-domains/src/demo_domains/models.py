from dipdup.models import Model
from tortoise import fields


class ExampleModel(Model):
    id = fields.IntField(pk=True)
    ...
