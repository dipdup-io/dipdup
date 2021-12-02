from contextlib import AsyncExitStack
from datetime import datetime
from functools import partial

from apscheduler.executors.asyncio import AsyncIOExecutor  # type: ignore
from apscheduler.jobstores.memory import MemoryJobStore  # type: ignore
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore
from apscheduler.util import undefined  # type: ignore
from pytz import utc

from dipdup.config import JobConfig
from dipdup.context import DipDupContext
from dipdup.context import HookContext
from dipdup.exceptions import ConfigurationError
from dipdup.utils import FormattedLogger
from dipdup.utils.database import in_global_transaction

jobstores = {
    'default': MemoryJobStore(),
}
executors = {
    'default': AsyncIOExecutor(),
}


def create_scheduler() -> AsyncIOScheduler:
    return AsyncIOScheduler(
        jobstores=jobstores,
        executors=executors,
        timezone=utc,
    )


def add_job(ctx: DipDupContext, scheduler: AsyncIOScheduler, job_config: JobConfig) -> None:
    hook_config = job_config.hook_config

    async def _job_wrapper(ctx: DipDupContext, *args, **kwargs) -> None:
        nonlocal job_config, hook_config
        job_ctx = HookContext(
            config=ctx.config,
            datasources=ctx.datasources,
            callbacks=ctx.callbacks,
            logger=logger,
            hook_config=hook_config,
        )

        async with AsyncExitStack() as stack:
            if hook_config.atomic:
                await stack.enter_async_context(in_global_transaction())

            await job_ctx.fire_hook(hook_config.callback, *args, **kwargs)

            if job_config.daemon:
                raise ConfigurationError('Daemon jobs are intended to run forever')

    logger = FormattedLogger(
        name=f'dipdup.hooks.{hook_config.callback}',
        fmt=job_config.name + ': {}',
    )
    if job_config.crontab:
        trigger, next_run_time = CronTrigger.from_crontab(job_config.crontab), undefined
    elif job_config.interval:
        trigger, next_run_time = IntervalTrigger(seconds=job_config.interval), undefined
    elif job_config.daemon:
        trigger, next_run_time = None, datetime.now()
    else:
        raise RuntimeError

    scheduler.add_job(
        func=partial(_job_wrapper, ctx=ctx),
        id=job_config.name,
        name=job_config.name,
        trigger=trigger,
        next_run_time=next_run_time,
        kwargs=job_config.args,
    )
