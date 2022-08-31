# custom

An arbitrary YAML object you can use to store internal indexer configuration.

```yaml
package: my_indexer
...
custom:
  foo: bar
```

Access or modify it from any callback:

```python
ctx.config.custom['foo'] = 'buzz'
```
