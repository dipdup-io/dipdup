# Logging

To control the number of logs DipDup produces, set the `logging` field in config:

```yaml
# setting logging root value will default logging level for all framework loggers
logging: fatal|error|warn|info|debug|default|verbose|quiet

# you can change logging level of specific loggers using
logging:
  dipdup: warn  # dipdup is a root(or default) logger for framework
  dipdup.cli: debug
```
default, verbose and quiet are info, debug and warn levels accordingly.

| Logger Name | Description |
| --- | --- |
| dipdup | Root logger |
| dipdup.cli | Messages related to DipDup's command-line interface (CLI) |
| dipdup.callback |  |
| dipdup.database |  |
| dipdup.http |  |
| dipdup.hasura |  |
| dipdup.project |  |
| dipdup.jobs |  |
| dipdup.datasource |  |
| dipdup.yaml |  |
| dipdup.codegen |  |
| dipdup.config |  |
| dipdup.tzkt |  |
| dipdup.subsquid |  |
| dipdup.matcher |  |
| dipdup.fetcher |  |
| dipdup.model |  |


If you need more fined tuning, perform it in the `on_restart` hook:

```python
import logging

async def on_restart(
    ctx: HookContext,
) -> None:
    logging.getLogger('some_logger').setLevel('DEBUG')
```
