from typing import TYPE_CHECKING
from typing import Type

from tortoise import Model
from tortoise.fields import CASCADE
from tortoise.fields import OneToOneField
from tortoise.fields import OneToOneRelation
from tortoise.fields import UUIDField

from dipdup.executors.models.operation_model import BlockchainOperationModel

if TYPE_CHECKING:  # pragma: no cover
    from dipdup.config import DatasourceConfigT

from dipdup.executors.config import WalletConfigInterface
from dipdup.executors.fsm.status import ExecutorOperationStatus
from dipdup.models import OperationData


class ExecutorTrackerModel(Model):
    id: UUIDField(pk=True)
    operation_id: Type[OperationData.id]
    wallet: WalletConfigInterface
    datasource: DatasourceConfigT
    operation: OneToOneRelation[BlockchainOperationModel] = OneToOneField(
        "models.Operation", on_delete=CASCADE, related_name="operation"
    )

    status: str

    def lock_for_tracking(self):
        self.status = ExecutorOperationStatus.locked
