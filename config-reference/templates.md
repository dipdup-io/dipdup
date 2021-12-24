# templates

Templates allow you to reuse index configuration, e.g., for different networks (mainnet/testnet) or multiple contracts sharing the same codebase. DipDup supports static and dynamic template instances.

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

## Placeholders

Templates have the same syntax as [indexes](indexes/README.md) of all kinds; the only difference is that they additionally support placeholders enabling parameterization:

```yaml
field: <placeholder>
```

Any string value wrapped in angle brackets is treated as a placeholder, so make sure there are no collisions with the actual values. You can use a single placeholder multiple times.

Any index implementing a template must have a value for each existing placeholder; all those values are then accessible via the handler context.

## Dynamic instances

DipDup allows spawning new indexes from a template in runtime. There are two ways to do that:

* From another index (e.g., handling factory originations)
* From the [configuration handler](../cli-reference/dipdup-run.md#custom-initialization)

> ⚠ **WARNING**
>
> DipDup is currently not able to automatically generate types and handlers for template indexes unless there is at least one [static instance](indexes/template.md).

DipDup exposes several context methods that extend the current configuration with new contracts and template instances. See [5.8. Handler context](../advanced/handler-context.md) for details.
