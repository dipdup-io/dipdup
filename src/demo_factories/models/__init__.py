
from dipdup import fields
from dipdup.models import Model


class Transfer(Model):
    id = fields.IntField(pk=True)
    from_ = fields.TextField()
    to = fields.TextField()
    amount = fields.TextField()