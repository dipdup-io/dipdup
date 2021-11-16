from tortoise.fields import CharField, IntField, UUIDField
from tortoise.models import Model

from dipdup.models import TimestampAwareMixin


class BlockchainOperationModel(Model, TimestampAwareMixin):
    id: UUIDField(pk=True)
    hash: CharField
    source: CharField
    destination: CharField
    parameters: CharField
    chain_id: CharField
    protocol: CharField
    branch: IntField
    gas_limit: IntField
    storage_limit: IntField
    fee: IntField
    ttl: IntField
    status: CharField
    executor: CharField
    level: IntField
