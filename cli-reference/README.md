# Command-line reference

## Installation

Python 3.8+ is required.

```shell
pip install dipdup
```

Check that DipDup CLI has been successfully installed:

```shell
dipdup --version
```

## Custom config name

By default DipDup is looking for a file named `dipdup.yml` in the current working directory. You can override that by explicitly telling where to find the config \(one or many\):

```shell
dipdup -c path/to/config.yml -c path/to/override/config.yml COMMAND
```

## Advanced Python logging

You may want to tune logging to get notifications on errors or enable debug messages. Specify path to a Python logging config in YAML format using `--logging-config` argument.

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
