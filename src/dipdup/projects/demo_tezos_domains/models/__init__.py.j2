from dipdup import fields
from dipdup.models import Model


class TLD(Model):
    id = fields.CharField(max_length=511, primary_key=True)
    owner = fields.CharField(max_length=36)


class Expiry(Model):
    id = fields.CharField(max_length=512, primary_key=True)
    expires_at = fields.DatetimeField(null=True)


class Domain(Model):
    id = fields.CharField(max_length=511, primary_key=True)
    tld: fields.ForeignKeyField[TLD] = fields.ForeignKeyField('models.TLD', 'domains')
    owner = fields.CharField(max_length=36)
    token_id = fields.BigIntField(null=True)
    expires_at = fields.DatetimeField(null=True)

    records: fields.ReverseRelation['Record']


class Record(Model):
    id = fields.CharField(max_length=511, primary_key=True)
    domain: fields.ForeignKeyField[Domain] = fields.ForeignKeyField('models.Domain', 'records')
    address = fields.CharField(max_length=36, null=True, db_index=True)
    expired = fields.BooleanField(default=False)
    metadata = fields.JSONField(null=True)