from dipdup import fields
from dipdup.models import Model


class Cursor(Model):
    """Singleton row rewritten on every level: deleted and re-created under a new PK.

    Mirrors the cursor bookkeeping real indexers do; the unique constraint on a
    non-PK pair is what turns a stranded model update into a hard failure.
    """

    id = fields.BigIntField(primary_key=True)
    level = fields.IntField()
    index = fields.IntField()

    class Meta:
        table = 'cursor'
        unique_together = ('level', 'index')
