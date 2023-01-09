import asyncio
import json
import logging
from contextlib import suppress
from functools import partial
from typing import Any
from typing import Dict
from typing import Optional
from typing import Set

from apscheduler.events import EVENT_JOB_ERROR  # type: ignore[import]
from apscheduler.events import EVENT_JOB_EXECUTED
from apscheduler.events import JobEvent
from apscheduler.job import Job  # type: ignore[import]
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import]
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore[import]

from dipdup.config import JobConfig
from dipdup.context import DipDupContext
from dipdup.context import HookContext
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import FrameworkException
from dipdup.utils import FormattedLogger

DEFAULT_CONFIG = {
    'apscheduler.jobstores.default.class': 'apscheduler.jobstores.memory:MemoryJobStore',
    'apscheduler.executors.default.class': 'apscheduler.executors.asyncio:AsyncIOExecutor',
    'apscheduler.timezone': 'UTC',
}


def _verify_config(config: Dict[str, Any]) -> None:
    """Ensure that dict is a valid `apscheduler` config"""
    json_config = json.dumps(config)
    if 'apscheduler.executors.pool' in json_config:
        raise ConfigurationError(
            '`apscheduler.executors.pool` is not supported. If needed, create a pool inside a regular hook.'
        )
    for key in config:
        if not key.startswith('apscheduler.'):
            raise ConfigurationError(
                '`advanced.scheduler` config keys must start with `apscheduler.`, see apscheduler library docs'
            )


class SchedulerManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        if config:
            _verify_config(config)
        self._logger = logging.getLogger('dipdup.jobs')
        self._scheduler = AsyncIOScheduler(config or DEFAULT_CONFIG)
        self._scheduler.add_listener(self._on_error, EVENT_JOB_ERROR)
        self._scheduler.add_listener(self._on_executed, EVENT_JOB_EXECUTED)
        self._exception: Optional[Exception] = None
        self._exception_event: asyncio.Event = asyncio.Event()
        self._daemons: Set[str] = set()

    async def run(self, event: asyncio.Event) -> None:
        self._logger.info('Waiting for an event to start scheduler')
        await event.wait()

        self._logger.info('Starting scheduler')
        try:
            self._scheduler.start()
            await self._exception_event.wait()
            if self._exception is None:
                raise FrameworkException('Job has failed but exception is not set')
            raise self._exception
        except asyncio.CancelledError:
            pass
        finally:
            self._scheduler.shutdown()

    def add_job(self, ctx: DipDupContext, job_config: JobConfig) -> Job:
        if job_config.daemon:
            self._daemons.add(job_config.name)

        hook_config = job_config.hook

        logger = FormattedLogger(
            name=f'dipdup.hooks.{hook_config.callback}',
            fmt=job_config.name + ': {}',
        )

        async def _job_wrapper(
            ctx: DipDupContext,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            nonlocal job_config, hook_config
            job_ctx = HookContext(
                config=ctx.config,
                datasources=ctx.datasources,
                callbacks=ctx._callbacks,
                transactions=ctx._transactions,
                logger=logger,
                hook_config=hook_config,
            )
            with suppress(asyncio.CancelledError):
                await job_ctx.fire_hook(
                    hook_config.callback,
                    *args,
                    **kwargs,
                )

        if job_config.crontab:
            trigger = CronTrigger.from_crontab(job_config.crontab)
        elif job_config.interval:
            trigger = IntervalTrigger(seconds=job_config.interval)
        elif job_config.daemon:
            trigger = None
        else:
            raise FrameworkException('Job config must have a trigger; check earlier')

        return self._scheduler.add_job(
            func=partial(_job_wrapper, ctx=ctx),
            id=job_config.name,
            name=job_config.name,
            trigger=trigger,
            kwargs=job_config.args,
        )

    def _on_error(self, event: JobEvent) -> None:
        self._exception = event.exception
        self._exception_event.set()

    def _on_executed(self, event: JobEvent) -> None:
        if event.job_id in self._daemons:
            event.exception = ConfigurationError('Daemon jobs are intended to run forever')
            self._on_error(event)
