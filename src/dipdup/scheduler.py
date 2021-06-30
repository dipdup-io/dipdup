from apscheduler.executors.asyncio import AsyncIOExecutor  # type: ignore
from apscheduler.jobstores.memory import MemoryJobStore  # type: ignore
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
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
    async def _atomic_wrapper(ctx, args):
        async with in_global_transaction():
            await job_config.callback_fn(ctx, args)

    trigger = CronTrigger.from_crontab(job_config.crontab)
    scheduler.add_job(
        func=_atomic_wrapper if job_config.atomic else job_config.callback_fn,
        id=job_name,
        name=job_name,
        trigger=trigger,
        kwargs=dict(
            ctx=ctx,
            args=job_config.args,
        ),
    )
