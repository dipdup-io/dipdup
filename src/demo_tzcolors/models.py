from enum import IntEnum

from tortoise import Model, fields


class AuctionStatus(IntEnum):
    ACTIVE = 0
    FINISHED = 1


class Address(Model):
    address = fields.CharField(36, pk=True)

    class Meta:
        table = 'addresses'


class Token(Model):
    id = fields.BigIntField(pk=True)
    address = fields.CharField(36)
    amount = fields.BigIntField()
    level = fields.BigIntField()
    timestamp = fields.DatetimeField()
    holder = fields.ForeignKeyField('models.Address', 'tokens')

    class Meta:
        table = 'tokens'


class Auction(Model):
    id = fields.BigIntField(pk=True)
    token = fields.ForeignKeyField('models.Token', 'auctions')
    bid_amount = fields.BigIntField()
    bidder = fields.ForeignKeyField('models.Address', 'winning_auctions')
    seller = fields.ForeignKeyField('models.Address', 'created_auctions')
    end_timestamp = fields.DatetimeField()
    status = fields.IntEnumField(AuctionStatus)
    level = fields.BigIntField()
    timestamp = fields.DatetimeField()

    class Meta:
        table = 'auctions'


class Bid(Model):
    id = fields.BigIntField(pk=True)
    auction = fields.ForeignKeyField('models.Auction', 'bids')
    bid_amount = fields.BigIntField()
    bidder = fields.ForeignKeyField('models.Address', 'bids')
    level = fields.BigIntField()
    timestamp = fields.DatetimeField()
