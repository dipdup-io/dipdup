from enum import IntEnum

from tortoise import Model, fields


class AuctionStatus(IntEnum):
    ACTIVE = 0
    FINISHED = 1


class Address(Model):
    address = fields.CharField(36, pk=True)


class Bid(Model):
    id = fields.IntField(pk=True)
    auction = fields.ForeignKeyField('models.Auction', 'bids')
    bidder = fields.ForeignKeyField('models.Address', 'bids')
    bid = fields.IntField()


class Auction(Model):
    label = fields.CharField(512, pk=True)
    ownership_period = fields.IntField()
    status = fields.IntEnumField(AuctionStatus)
    ends_at = fields.DatetimeField()


class Domain(Model):
    label = fields.CharField(512, pk=True)
    name = fields.CharField(512)
    qualname = fields.CharField(512)
    address = fields.ForeignKeyField('models.Address', 'pointed_domains', null=True)
    owner = fields.ForeignKeyField('models.Address', 'owned_domains')
    parent = fields.ForeignKeyField('models.Domain', 'subdomains', null=True)
    expires_at = fields.DatetimeField(null=True)
    token = fields.IntField(null=True)
