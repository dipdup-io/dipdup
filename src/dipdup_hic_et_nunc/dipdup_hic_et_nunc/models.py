from tortoise import Model, fields


class ExampleModel(Model):
    id = fields.IntField(pk=True)
    ...

    class Meta:
        table = 'example_models'