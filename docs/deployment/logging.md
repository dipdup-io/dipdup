# Logging

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

Currently, you have two options to configure logging:

1. Manually in `on_restart` hook

```python
import logging

async def on_restart(
    ctx: HookContext,
) -> None:
    logging.getLogger('my_logger').setLevel('DEBUG')
```

2. With Python logging config

```shell
dipdup -l logging.yml run
```

Example config:

```yaml
version: 1
disable_existing_loggers: false
formatters:
  brief:
    format: "%(levelname)-8s %(name)-20s %(message)s"
handlers:
  console:
    level: INFO
    formatter: brief
    class: logging.StreamHandler
    stream: ext://sys.stdout
loggers:
  dipdup:
    level: INFO

  aiosqlite:
    level: INFO
  db_client:
    level: INFO
root:
  level: INFO
  handlers:
    - console
```
