from tortoise import fields

from dipdup.models import Model


class Holder(Model):
    address = fields.CharField(max_length=42, pk=True)
    balance = fields.DecimalField(decimal_places=6, max_digits=20, default=0)
    turnover = fields.DecimalField(decimal_places=6, max_digits=20, default=0)
    tx_count = fields.BigIntField(default=0)
    last_seen = fields.BigIntField(null=True)
