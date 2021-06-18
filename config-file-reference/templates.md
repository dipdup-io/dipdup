---
description: Indexes block
---

# templates

Templates allows you to reuse index configuration, e.g. for different networks \(mainnet/testnet\) or for multiple contracts sharing the same codebase. DipDup supports static and dynamic template instances.

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

Templates have the same syntax as [indexes](indexes/) of all kinds, the only difference is that they additionally support placeholders enabling parameterization:

```yaml
field: <placeholder>
```

Any string value wrapped in angle brackets is treated as a placeholder, so make sure there are not collisions with the real values. You can use a single placeholder multiple times.

Any index implementing a template has to have a value for each existing placeholder, all those values are then accessible via the handler context.

## Dynamic instances

DipDup allows to spawn new indexes from a template in runtime. There are two ways to do that:

* From another index \(e.g. handling factory originations\)
* From the [configuration handler](../command-line/dipdup-run.md#custom-initialization)

DipDup exposes several context methods that extend current configuration with new contracts and template instances.

{% page-ref page="../advanced/context-helpers.md" %}

