# Templates and variables

Templates allow you to reuse index configuration, e.g., for different networks (mainnet/testnet) or multiple contracts sharing the same codebase.

```yaml
templates:
  my_template:
    kind: operation
    datasource: <datasource>
    contracts:
      - <contract1>
    handlers:
      - callback: callback1
        pattern:
          - destination: <contract1>
            entrypoint: call
```

Templates have the same syntax as [indexes](../config/indexes/README.md) of all kinds; the only difference is that they additionally support placeholders enabling parameterization:

```yaml
field: <placeholder>
```

Any string value wrapped in angle brackets is treated as a placeholder, so make sure there are no collisions with the actual values. You can use a single placeholder multiple times.

Any index implementing a template must have a value for each existing placeholder; the exception raised otherwise. Those values are within the handler context at `ctx.template_values`.

> 🤓 **SEE ALSO**
>
> * {{ #summary advanced/index-factories.md }}
> * {{ #summary config/templates.md }}
