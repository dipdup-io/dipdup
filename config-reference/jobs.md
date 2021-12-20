# jobs

In some cases, it may come in handy to have the ability to run some code on schedule. For example, you want to calculate statistics once per hour instead of every time handler gets matched.

Note that jobs are actually schedules for [hooks](hooks.md).

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

### Arguments typechecking

DipDup will ensure that arguments passed to the hooks have correct types when possible. `CallbackTypeError` exception will be raised otherwise. Values of an `args` mapping in a hook config should be either built-in types or `__qualname__` of external type like `decimal.Decimal`. Generic types are not supported: hints like `Optional[int] = None` will be correctly parsed during codegen but ignored on type checking.

### [\#](https://baking-bad.org/blog/2021/09/13/dipdup-v3-release-candidate-introducing-hooks-better-scalability-and-stability-improvements/#context-ctx) <a id="context-ctx"></a>
