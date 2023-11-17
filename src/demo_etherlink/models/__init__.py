import enum

from dipdup import fields
from dipdup.models import Model


class ExampleModel(Model):
    id = fields.IntField(pk=True)
    array = fields.ArrayField()
    big_int = fields.BigIntField()
    binary = fields.BinaryField()
    boolean = fields.BooleanField()
    decimal = fields.DecimalField(10, 2)
    date = fields.DateField()
    datetime = fields.DatetimeField()
    enum_ = fields.EnumField(enum.Enum)
    float = fields.FloatField()
    int_enum = fields.IntEnumField(enum.IntEnum)
    int_ = fields.IntField()
    json = fields.JSONField()
    small_int = fields.SmallIntField()
    text = fields.TextField()
    time_delta = fields.TimeDeltaField()
    time = fields.TimeField()
    uuid = fields.UUIDField()

    relation: fields.ForeignKeyField['ExampleModel'] = fields.ForeignKeyField(
        'models.ExampleModel', related_name='reverse_relation'
    )
    m2m_relation: fields.ManyToManyField['ExampleModel'] = fields.ManyToManyField(
        'models.ExampleModel', related_name='reverse_m2m_relation'
    )

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    relation_id: int
    m2m_relation_ids: list[int]

    class Meta:
        abstract = True
