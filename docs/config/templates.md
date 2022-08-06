# templates

```yaml
indexes:
  foo:
    kind: template
    name: bar
    first_level: 12341234
    template_values:
      network: mainnet

templates:
  bar:
    kind: index
    datasource: tzkt_<network>  # resolves into `tzkt_mainnet`
    ...
```

| field | description |
| - | - |
| `kind` | always `template` |
| `name` | Name of index template |
| `template_values` | Values to be substituted in template (`<key>` → `value`) |
| `first_level` | Level to start indexing from |
| `last_level` | Level to stop indexing at (DipDup will terminate at this level) |
