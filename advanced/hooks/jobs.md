# Job scheduler

Jobs are schedules for hooks. In some cases, it may come in handy to have the ability to run some code on schedule. For example, you want to calculate statistics once per hour instead of every time handler gets matched.

## Arguments typechecking

DipDup will ensure that arguments passed to the hooks have correct types when possible. `CallbackTypeError` exception will be raised otherwise. Values of an `args` mapping in a hook config should be either built-in types or `__qualname__` of external type like `decimal.Decimal`. Generic types are not supported: hints like `Optional[int] = None` will be correctly parsed during codegen but ignored on type checking.

See [12.8. jobs](../../config/jobs.md) for details.
