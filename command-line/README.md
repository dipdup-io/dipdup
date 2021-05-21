# Command-line reference

## Installation

{% tabs %}
{% tab title="Python" %}
Python 3.8+ is required.

```bash
pip install dipdup
```
{% endtab %}
{% endtabs %}

Check that DipDup CLI has been successfully installed:

```text
dipdup --version
```

## Custom config name



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





