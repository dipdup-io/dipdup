from tortoise import Model, fields


class Address(Model):
    address = fields.CharField(59, pk=True)


class Token(Model):
    id = fields.IntField(pk=True)
    address = fields.CharField(59)
    amount = fields.IntField()
    level = fields.IntField()
    timestamp = fields.DatetimeField()
    holder = fields.ForeignKeyField('models.Address', 'tokens')

    class Meta:
        table = 'tokens'


class Auction(Model):
    id = fields.IntField(pk=True)
    token_address = fields.CharField(59)
    token_id = fields.IntField()
    token_amount = fields.IntField()
    bid_amount = fields.IntField()
    bidder = fields.ForeignKeyField('models.Address', 'winning_auctions')
    seller = fields.ForeignKeyField('models.Address', 'created_auctions')
    end_timestamp = fields.DatetimeField()
    level = fields.IntField()
    timestamp = fields.DatetimeField()

    class Meta:
        table = 'auctions'


class Bid(Model):
    id = fields.IntField(pk=True)
    token_id = fields.IntField()
    bidder = fields.ForeignKeyField('models.Address', 'bids')
    level = fields.IntField()
    timestamp = fields.DatetimeField()
