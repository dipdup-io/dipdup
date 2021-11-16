from typing import TYPE_CHECKING

from dipdup.const import OperationType
from dipdup.executors.dto.operation_dto import OperationFeeData, OperationFields, OperationParameters, TransactionOperationDTO

if TYPE_CHECKING:
    from dipdup.config import OperationHandlerTransactionPatternConfig
    from dipdup.context import DipDupContext


class TransactionBuilder:
    def __init__(
            self,
            context: DipDupContext,
            handler: OperationHandlerTransactionPatternConfig
    ):
        self._context: DipDupContext = context
        self._handler: OperationHandlerTransactionPatternConfig = handler
        self._operation_parameters: OperationParameters

    def _prepare_parameters(self) -> None:
        self._operation_parameters = OperationParameters(
            dst=self._handler.destination.address,
            entrypoint=self._handler.entrypoint,
        )

    def _prepare_fields(self) -> None:
        self._operation_parameters = OperationFields()

    def _prepare_fee_data(self) -> None:
        self._operation_fee_data = OperationFeeData()

    def build(self) -> TransactionOperationDTO:
        dto = TransactionOperationDTO(
            type=OperationType.transaction,
            dst=self._operation_parameters.dst,
            entrypoint=self._operation_parameters.entrypoint,
            gas_limit=self._operation_fee_data.gas_limit,
            storage_limit=self._operation_fee_data.storage_limit,
            storage_fee=self._operation_fee_data.storage_fee,
        )

        return dto

