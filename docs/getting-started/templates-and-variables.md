# Templates and variables

## Environment variables

DipDup supports compose-style variable expansion with optional default value:

```yaml
database:
  kind: postgres
  host: ${POSTGRES_HOST:-localhost}
  password: ${POSTGRES_PASSWORD}
```

You can use environment variables anywhere throughout the configuration file. Consider the following example (absolutely useless but illustrative):

```yaml
custom:
  ${FOO}: ${BAR:-bar}
  ${FIZZ:-fizz}: ${BUZZ}
```

Running `FOO=foo BUZZ=buzz dipdup config export --unsafe` will produce the following output:

```yaml
custom:
  fizz: buzz
  foo: bar
```

Use this feature to store sensitive data outside of the configuration file and make your app fully declarative.

## Index templates

Templates allow you to reuse index configuration, e.g., for different networks (mainnet/ghostnet) or multiple contracts sharing the same codebase.

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

Templates have the same syntax as indexes of all kinds; the only difference is that they additionally support placeholders enabling parameterization:

```yaml
field: <placeholder>
```

The template above can be resolved in the following way:

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

Any string value wrapped in angle brackets is treated as a placeholder, so make sure there are no collisions with the actual values. You can use a single placeholder multiple times. In contradiction to environment variables, dictionary keys cannot be placeholders.

An index created from a template must have a value for each placeholder; the exception is raised otherwise. These values are available in the handler context as `ctx.template_values` dictionary.

You can also spawn indexes from templates in runtime. To achieve the same effect as above, you can use the following code:

```python
ctx.add_index(
    name='my_template_instance',
    template='my_template',
    values={
        'datasource': 'tzkt_mainnet',
        'contract': 'some_dex',
    },
)
```

> 💡 **SEE ALSO**
>
> * {{ #summary advanced/index-factories.md }}
> * {{ #summary config/templates.md }}
