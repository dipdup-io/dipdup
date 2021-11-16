from dipdup.executors.models.operation_model import OperationModel


class OperationTracker:
    ...

    async def provide(self):
        for operation in await OperationModel.get_or_none(...):
            operation.lock_for_tracking()
            yield operation


