# Improving performance

This page contains tips that may help to increase indexing speed.

## Optimize database schema

[Postgres indexes](https://www.postgresql.org/docs/9.5/indexes-types.html) are tables that Postgres can use to speed up data lookup. A database index acts like a pointer to data in a table, just like an index in a printed book. If you look in the index first, you will find the data much quicker than searching the whole book (or — in this case — database).

You should add indexes on columns often appearing in `WHERE`` clauses in your GraphQL queries and subscriptions.

Tortoise ORM uses BTree indexes by default. To set index on a field, add `index=True` to the field definition:

```python
from dipdup.models import Model
from tortoise import fields


class Trade(Model):
    id = fields.BigIntField(pk=True)
    amount = fields.BigIntField()
    level = fields.BigIntField(index=True)
    timestamp = fields.DatetimeField(index=True)
```

## Tune datasources

All datasources now share the same code under the hood to communicate with underlying APIs via HTTP. Configs of all datasources and also Hasura's one can have an optional section `http` with any number of the following parameters set:

```yaml
datasources:
  tzkt:
    kind: tzkt
    ...
    http:
      retry_count: 10
      retry_sleep: 1
      retry_multiplier: 1.2
      ratelimit_rate: 100
      ratelimit_period: 60
      connection_limit: 25
      batch_size: 10000
hasura:
  url: http://hasura:8080
  http:
    ...
```

| field | description |
| - | - |
| `retry_count` | Number of retries after request failed before giving up |
| `retry_sleep` | Sleep time between retries |
| `retry_multiplier` | Multiplier for sleep time between retries |
| `ratelimit_rate` | Number of requests per period ("drops" in leaky bucket) |
| `ratelimit_period` | Period for rate limiting in seconds |
| `connection_limit` | Number of simultaneous connections |
| `connection_timeout` | Connection timeout in seconds |
| `batch_size` | Number of items fetched in a single paginated request (for some APIs) |

Each datasource has its defaults. Usually, there's no reason to alter these settings unless you use self-hosted instances of TzKT or other datasource.

By default, DipDup retries failed requests infinitely, exponentially increasing the delay between attempts. Set `retry_count` parameter to limit the number of attempts.

`batch_size` parameter is TzKT-specific. By default, DipDup limit requests to 10000 items, the maximum value allowed on public instances provided by Baking Bad. Decreasing this value will reduce the time required for TzKT to process a single request and thus reduce the load. By reducing the `connection_limit` parameter, you can achieve the same effect (limited to synchronizing multiple indexes concurrently).

> 💡 **SEE ALSO**
>
> * [Tortoise ORM documentation](https://tortoise-orm.readthedocs.io/en/latest/)
> * [Tortoise ORM examples](https://tortoise-orm.readthedocs.io/en/latest/examples.html)
> * {{ #summary deployment/database-engines.md}}
> * {{ #summary deployment/backups.md}}

See [12.4. datasources](../config/datasources.md) for details.

## Use TimescaleDB for time-series

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

DipDup is fully compatible with [TimescaleDB](https://docs.timescale.com/). Try its "continuous aggregates" feature, especially if dealing with market data like DEX quotes.

## Cache commonly used models

If your indexer contains models having few fields and used primarily on relations, you can cache such models during synchronization.

Example code:

```python
class Trader(Model):
    address = fields.CharField(36, pk=True)


class TraderCache:
    def __init__(self, size: int = 1000) -> None:
        self._size = size
        self._traders: OrderedDict[str, Trader] = OrderedDict()

    async def get(self, address: str) -> Trader:
        if address not in self._traders:
            # NOTE: Already created on origination
            self._traders[address], _ = await Trader.get_or_create(address=address)
              if len(self._traders) > self._size:
                self._traders.popitem(last=False)

        return self._traders[address]

trader_cache = TraderCache()
```

Use `trader_cache.get` in handlers. After sync is complete, you can clear this cache to free some RAM:

```python
async def on_synchronized(
    ctx: HookContext,
) -> None:
    ...
    models.trader_cache.clear()
```

## Perform heavy computations in separate processes

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
