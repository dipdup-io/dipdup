# Multiprocessing

It's impossible to use `apscheduler` pool executors with hooks because `HookContext` is not pickle-serializable. So, they are forbidden now in `advanced.scheduler` config. However, thread/process pools can come in handy in many situations, and it would be nice to have them in DipDup context. For now, I can suggest implementing custom commands as a workaround to perform any resource-hungry tasks within them. Put the following code in `<project>/cli.py`:

```python
from contextlib import AsyncExitStack

import asyncclick as click
from dipdup.cli import cli, cli_wrapper
from dipdup.config import DipDupConfig
from dipdup.context import DipDupContext
from dipdup.utils.database import tortoise_wrapper


@cli.command(help='Run heavy calculations')
@click.pass_context
@cli_wrapper
async def do_something_heavy(ctx):
    config: DipDupConfig = ctx.obj.config
    url = config.database.connection_string
    models = f'{config.package}.models'

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(tortoise_wrapper(url, models))
        ...

if __name__ == '__main__':
    cli(prog_name='dipdup', standalone_mode=False)  # type: ignore
```

Then use `python -m <project>.cli` instead of `dipdup` as an entrypoint. Now you can call `do-something-heavy` like any other `dipdup` command. `dipdup.cli:cli` group handles arguments and config parsing, graceful shutdown, and other boilerplate. The rest is on you; use `dipdup.dipdup:DipDup.run` as a reference. And keep in mind that Tortoise ORM is not thread-safe. I aim to implement `ctx.pool_apply` and `ctx.pool_map` methods to execute code in pools with _magic_ within existing DipDup hooks, but no ETA yet.
