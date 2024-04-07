from dipdup import fields
from dipdup.models import Model


class Transaction(Model):
    hash = fields.TextField(pk=True)
    block_number = fields.IntField()
    from_ = fields.TextField()
    to = fields.TextField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
