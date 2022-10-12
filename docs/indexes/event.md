# `event` index

Kathmandu Tezos protocol upgrade has introduced [contract events](https://tezos.gitlab.io/alpha/event.html), a new way to interact with smart contracts. This index allows indexing events using strictly typed payloads. From the developer's perspective, it's similar to the `big_map` index with a few differences.

An example below is artificial since no known contracts in mainnet are currently using events.

```yaml
{{ #include ../../demos/demo-events/dipdup.yml:23:32 }}
```

Unlike big maps, contracts may introduce new event tags and payloads at any time, so the index must be updated accordingly.

```python
{{ #include ../../demos/demo-events/src/demo_events/handlers/on_events_xrate.py:7: }}
```

Each contract can have a fallback handler called for all unknown events so you can process untyped data.

```python
{{ #include ../../demos/demo-events/src/demo_events/handlers/on_events_unknown.py:6: }}
```
