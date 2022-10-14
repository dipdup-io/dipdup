# Job scheduler

Jobs are schedules for hooks. In some cases, it may come in handy to have the ability to run some code on schedule. For example, you want to calculate statistics once per hour instead of every time handler gets matched.

Add the following section to the DipDup config:

```yaml
jobs:
  midnight_stats:
    hook: calculate_stats
    crontab: "0 0 * * *"
    args:
      major: True
  leet_stats:
    hook: calculate_stats
    interval: 1337  # in seconds
    args:
      major: False
```

If you're unfamiliar with the crontab syntax, an online service [crontab.guru](https://crontab.guru/) will help you build the desired expression.

## Scheduler configuration

DipDup utilizes `apscheduler` library to run hooks according to schedules in `jobs` config section. In the following example, `apscheduler` will spawn up to three instances of the same job every time the trigger is fired, even if previous runs are in progress:

```yaml
advanced:
  scheduler:
    apscheduler.job_defaults.coalesce: True
    apscheduler.job_defaults.max_instances: 3
```

See [`apscheduler` docs](https://apscheduler.readthedocs.io/en/stable/userguide.html#configuring-the-scheduler) for details.

Note that you can't use executors from `apscheduler.executors.pool` module - `ConfigurationError` exception will be raised.
