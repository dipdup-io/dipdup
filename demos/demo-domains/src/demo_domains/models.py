from tortoise import fields
from tortoise.fields.relational import ForeignKeyFieldInstance

from dipdup.models import Model


class TLD(Model):
    id = fields.TextField(pk=True)
    owner = fields.TextField()


class Domain(Model):
    id = fields.TextField(pk=True)
    tld: ForeignKeyFieldInstance[TLD] = fields.ForeignKeyField('models.TLD', 'domains')
    expiry = fields.DatetimeField(null=True)
    owner = fields.TextField()
    token_id = fields.BigIntField(null=True)

    tld_id: str | None


class Record(Model):
    id = fields.TextField(pk=True)
    domain: ForeignKeyFieldInstance[Domain] = fields.ForeignKeyField('models.Domain', 'records')
    address = fields.TextField(null=True)
