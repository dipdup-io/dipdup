---
description: Jobs block
---

# jobs

In some cases, it may come in handy to have an ability to run some code on schedule. For example, you want to calculate some statistics once per hour, not on every block. Add the following section to DipDup config:

```yaml
jobs:
  midnight_stats:
    callback: calculate_stats
    crontab: "0 0 * * *"
    args:
      major: True
    atomic: True
  leet_stats:
    callback: calculate_stats
    interval: 1337  # in seconds
    args:
      major: False
    atomic: True
```

Run `dipdup init` to generate according handlers in the `jobs` directory. A single callback can be reused with different arguments.

When `atomic` parameter is set, the job will be wrapped in SQL transaction and rolled back in case of failure.

If you're not familiar with the crontab syntax, there's an online service [crontab.guru \(opens new window\)](https://crontab.guru/) that will help you to build a desired expression.

