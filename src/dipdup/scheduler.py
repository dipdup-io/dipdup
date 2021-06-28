from apscheduler.executors.asyncio import AsyncIOExecutor  # type: ignore
from apscheduler.jobstores.memory import MemoryJobStore  # type: ignore
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from pytz import utc

from dipdup.config import JobConfig

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


def add_job(scheduler: AsyncIOScheduler, job_config: JobConfig) -> None:
    if job_config.atomic:
        raise NotImplementedError
    trigger = CronTrigger.from_crontab(job_config.crontab)
    scheduler.add_job(
        func=job_config.callback_fn,
        id=job_config.callback,
        name=job_config.callback,
        trigger=trigger,
        kwargs=job_config.args,
    )
