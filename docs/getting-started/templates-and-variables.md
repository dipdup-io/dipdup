# Templates and variables

## Index templates

Templates allow you to reuse index configuration, e.g., for different networks (mainnet/testnet) or multiple contracts sharing the same codebase.

```yaml
templates:
  my_template:
    kind: operation
    datasource: <datasource>
    contracts:
      - <contract>
    handlers:
      - callback: callback
        pattern:
          - destination: <contract>
            entrypoint: call
```

Templates have the same syntax as [indexes](../config/indexes/README.md) of all kinds; the only difference is that they additionally support placeholders enabling parameterization:

```yaml
field: <placeholder>
```

Template above can be resolved in a following way:

```yaml
contracts:
  some_dex: ...

datasources:
  tzkt: ...

indexes:
  my_template_instance:
    template: my_template
    values:
      datasource: tzkt_mainnet
      contract: some_dex
```

Any string value wrapped in angle brackets is treated as a placeholder, so make sure there are no collisions with the actual values. You can use a single placeholder multiple times.

Any index implementing a template must have a value for each existing placeholder; the exception raised otherwise. These values are available in the handler context at `ctx.template_values`.

## Environment variables

DipDup supports compose-style variable expansion with optional default value:

```yaml
database:
  ...
  password: ${POSTGRES_PASSWORD:-changeme}
```

You can use environment variables throughout the configuration file, except for property names (YAML object keys).

> 💡 **SEE ALSO**
>
> * {{ #summary advanced/index-factories.md }}
> * {{ #summary config/templates.md }}
