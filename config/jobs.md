# jobs


Add the following section to DipDup config:

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

If you're not familiar with the crontab syntax, there's an online service [crontab.guru](https://crontab.guru/) that will help you build the desired expression.