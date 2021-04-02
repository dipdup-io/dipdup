from tortoise import Model, fields


class Address(Model):
    address = fields.CharField(58, pk=True)


class Token(Model):
    id = fields.IntField(pk=True)
    token_id = fields.IntField()
    token_info = fields.CharField(255)
    holder = fields.ForeignKeyField('models.Address', 'tokens')
    transaction = fields.ForeignKeyField('int_models.Transaction', 'tokens')
