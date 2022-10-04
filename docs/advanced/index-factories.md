# Index factories

DipDup allows creating new indexes in runtime. To begin with, you need to define index templates in the top-level `templates` section of the config. Then call `ctx.add_contract` and `ctx.add_index` methods from any user callback.

DipDup is currently not able to automatically generate types and handlers for template indexes unless there is at least one static instance ({{ #summary config/templates.md}}). Add it temporarily setting template values manually to call `dipdup init` command.

The most common way to spawn indexes is to create an index that tracks the originations of contracts with similar code or originated by a specific contract. A minimal example looks like this:

```yaml
contracts:
  registry:
    address: KT19CF3KKrvdW77ttFomCuin2k4uAVkryYqh

indexes:
  factory:
    kind: operation
    datasource: tzkt
    types:
      - origination
    handlers:
      - callback: on_factory_origination
        pattern:
          - type: origination
            similar_to: registry
```

Another solution is to implement custom logic in `on_restart` hook (see {{ #summary advanced/event-hooks.md#on_restart}})

> 💡 **SEE ALSO**
>
> * {{ #summary advanced/context.md}}
> * {{ #summary config/templates.md}}
