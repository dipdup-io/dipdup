# Command-line reference

If you have not installed DipDup yet refer to [4.1. Installation](../getting-started/installation.md) page.

## Specifying the path to config

By default, DipDup looks for a file named `dipdup.yml` in the current working directory. You can override that by explicitly specifying a path to config (one or many):

```shell
dipdup -c configs/dipdup.yml -c configs/dipdup.prod.yml COMMAND
```

See [Merging config files](../config-reference#merging-config-files) for details.

## Advanced Python logging

> ⚠ **WARNING**
>
> This feature will be deprecated soon. Consider configuring logging inside of `on_restart` hook.

You may want to tune logging to get notifications on errors or enable debug messages. Specify the path to a Python logging config in YAML format using `-l` argument.

Default config to start with:

```yaml
version: 1
  disable_existing_loggers: false
  formatters:
    brief:
      format: "%(levelname)-8s %(name)-35s %(message)s"
  handlers:
    console:
      level: INFO
      formatter: brief
      class: logging.StreamHandler
      stream : ext://sys.stdout
  loggers:
    SignalRCoreClient:
      formatter: brief
    dipdup.datasources.tzkt.datasource:
      level: INFO
    dipdup.datasources.tzkt.cache:
      level: INFO
  root:
    level: INFO
    handlers:
      - console
```
