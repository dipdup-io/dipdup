from tortoise import Model, fields


class Address(Model):
    address = fields.CharField(36, pk=True)


class Domain(Model):
    label = fields.CharField(512, pk=True)
    name = fields.CharField(512)
    qualname = fields.CharField(512)
    address = fields.ForeignKeyField('models.Address', 'pointed_domains', null=True)
    owner = fields.ForeignKeyField('models.Address', 'owned_domains')
    parent = fields.ForeignKeyField('models.Domain', 'subdomains', null=True)
    expires_at = fields.DatetimeField()
    token = fields.IntField()
