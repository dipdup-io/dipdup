from dipdup import fields
from dipdup.models import Model


class Transfer(Model):
    id = fields.IntField(primary_key=True)
    from_ = fields.TextField()
    to = fields.TextField()
    amount = fields.TextField()
