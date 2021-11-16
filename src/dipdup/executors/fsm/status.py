from enum import Enum
from typing import Callable
from typing import TYPE_CHECKING

from dipdup.executors.fsm.exception import InvalidStatusError

if TYPE_CHECKING:
    from dipdup.executors.models.tracker_model import ExecutorTrackerModel


class ExecutorOperationStatus(Enum):
    pending: str = 'pending'
    applied: str = 'applied'
    failed: str = 'failed'
    backtracked: str = 'backtracked'
    skipped: str = 'skipped'

    locked: str = 'locked'


class FSMTransitions:
    def __init__(self, tracker: ExecutorTrackerModel):
        self.tracker: ExecutorTrackerModel = tracker

    def set_status(self, status: ExecutorOperationStatus):
        try:
            change_status = getattr(self, f'_set_{status}')
            assert isinstance(change_status, Callable)

            change_status()
        except AttributeError:
            raise InvalidStatusError
        except InvalidStatusError:
            self._set_failed()

    def _set_pending(self):
        self._update_status(status=ExecutorOperationStatus.pending)

    def _set_applied(self):
        assert self.tracker.status == ExecutorOperationStatus.pending
        self._update_status(status=ExecutorOperationStatus.applied)

    def _set_backtracked(self):
        assert self.tracker.status == ExecutorOperationStatus.pending
        self._update_status(status=ExecutorOperationStatus.backtracked)

    def _set_skipped(self):
        assert self.tracker.status == ExecutorOperationStatus.pending
        self._update_status(status=ExecutorOperationStatus.skipped)

    def _set_failed(self):
        self._update_status(status=ExecutorOperationStatus.failed)

    def _update_status(self, status: ExecutorOperationStatus.value):
        self.tracker.status = status
        self.tracker.save()

        operation = self.tracker.operation
        operation.status = status
        operation.save()
