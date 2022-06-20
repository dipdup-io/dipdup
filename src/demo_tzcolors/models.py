from enum import IntEnum

from tortoise import ForeignKeyFieldInstance
from tortoise import Model
from tortoise import fields


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
    holder: ForeignKeyFieldInstance[Address] = fields.ForeignKeyField('models.Address', 'tokens')

    token_id: int

    class Meta:
        table = 'tokens'


class Auction(Model):
    id = fields.BigIntField(pk=True)
    token: ForeignKeyFieldInstance[Token] = fields.ForeignKeyField('models.Token', 'auctions')
    bid_amount = fields.BigIntField()
    bidder: ForeignKeyFieldInstance[Address] = fields.ForeignKeyField('models.Address', 'winning_auctions')
    seller: ForeignKeyFieldInstance[Address] = fields.ForeignKeyField('models.Address', 'created_auctions')
    end_timestamp = fields.DatetimeField()
    status = fields.IntEnumField(AuctionStatus)
    level = fields.BigIntField()
    timestamp = fields.DatetimeField()

    token_id: int

    class Meta:
        table = 'auctions'


class Bid(Model):
    id = fields.BigIntField(pk=True)
    auction: ForeignKeyFieldInstance[Auction] = fields.ForeignKeyField('models.Auction', 'bids')
    bid_amount = fields.BigIntField()
    bidder: ForeignKeyFieldInstance[Address] = fields.ForeignKeyField('models.Address', 'bids')
    level = fields.BigIntField()
    timestamp = fields.DatetimeField()
