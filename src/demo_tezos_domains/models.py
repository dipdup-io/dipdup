from tortoise import Model, fields


class TLD(Model):
    id = fields.CharField(max_length=255, pk=True)
    owner = fields.CharField(max_length=36)


class Domain(Model):
    id = fields.CharField(max_length=255, pk=True)
    tld = fields.ForeignKeyField('models.TLD', 'domains')
    expiry = fields.DatetimeField(null=True)
    owner = fields.CharField(max_length=36)
    token_id = fields.BigIntField(null=True)


class Record(Model):
    id = fields.CharField(max_length=255, pk=True)
    domain = fields.ForeignKeyField('models.Domain', 'records')
    address = fields.CharField(max_length=36, null=True)
