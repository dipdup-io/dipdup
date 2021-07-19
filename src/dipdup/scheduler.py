from contextlib import AsyncExitStack

from apscheduler.executors.asyncio import AsyncIOExecutor  # type: ignore
from apscheduler.jobstores.memory import MemoryJobStore  # type: ignore
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore
from pytz import utc

from dipdup.config import JobConfig
from dipdup.context import DipDupContext
from dipdup.utils import in_global_transaction

jobstores = {
    'default': MemoryJobStore(),
}
executors = {
    'default': AsyncIOExecutor(),
}
job_defaults = {
    'coalesce': False,
    'max_instances': 3,
}


def create_scheduler() -> AsyncIOScheduler:
    return AsyncIOScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone=utc,
    )


def add_job(ctx: DipDupContext, scheduler: AsyncIOScheduler, job_name: str, job_config: JobConfig) -> None:
    async def _wrapper(ctx, args) -> None:
        nonlocal job_config
        async with AsyncExitStack() as stack:
            if job_config.atomic:
                await stack.enter_async_context(in_global_transaction())
            await job_config.callback_fn(ctx, args)

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
            ctx=ctx,
            args=job_config.args,
        ),
    )
