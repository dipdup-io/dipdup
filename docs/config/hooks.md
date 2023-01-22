# hooks

Hooks are user-defined callbacks you can execute with a job scheduler or within another callback (with `ctx.fire_hook`).

```yaml
hooks:
  calculate_stats:
    callback: calculate_stats
    atomic: False
    args:
     major: bool
     depth: int
```

```admonish info title="See Also"
* {{ #summary advanced/hooks.md}}
```
