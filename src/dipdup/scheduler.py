from contextlib import AsyncExitStack

from apscheduler.executors.asyncio import AsyncIOExecutor  # type: ignore
from apscheduler.jobstores.memory import MemoryJobStore  # type: ignore
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore
from pytz import utc

from dipdup.config import JobConfig
from dipdup.context import DipDupContext, JobContext
from dipdup.utils import FormattedLogger, in_global_transaction

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


def add_job(ctx: DipDupContext, scheduler: AsyncIOScheduler, job_name: str, job_config: JobConfig) -> None:
    async def _wrapper(ctx, args) -> None:
        nonlocal job_config
        async with AsyncExitStack() as stack:
            if job_config.atomic:
                await stack.enter_async_context(in_global_transaction())
            await job_config.callback_fn(ctx, args)

    logger = FormattedLogger(
        name=job_config.callback,
        fmt=job_config.name + ': {}',
    )
    if job_config.crontab:
        trigger = CronTrigger.from_crontab(job_config.crontab)
    elif job_config.interval:
        trigger = IntervalTrigger(seconds=job_config.interval)
    scheduler.add_job(
        func=_wrapper,
        id=job_name,
        name=job_name,
        trigger=trigger,
        kwargs=dict(
            ctx=JobContext(
                config=ctx.config,
                datasources=ctx.datasources,
                logger=logger,
            ),
            args=job_config.args,
        ),
    )
