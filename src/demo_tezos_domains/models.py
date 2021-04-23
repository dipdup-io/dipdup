from tortoise import Model, fields


class Domain(Model):
    name = fields.CharField(max_length=255, pk=True)
    expiry = fields.DatetimeField()
    owner = fields.CharField(max_length=33)
    token_id = fields.BigIntField(null=True)


class Record(Model):
    name = fields.CharField(max_length=255, pk=True)
    domain = fields.ForeignKeyField('models.Domain', 'records')
    address = fields.CharField(max_length=33, null=True)
