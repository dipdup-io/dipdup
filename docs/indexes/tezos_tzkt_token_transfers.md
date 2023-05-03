# `tezos.tzkt.token_transfers` index

This index allows indexing token transfers of contracts compatible with [FA1.2](https://gitlab.com/tzip/tzip/-/blob/master/proposals/tzip-7/README.md) or [FA2](https://gitlab.com/tzip/tzip/-/blob/master/proposals/tzip-12/tzip-12.md) standards.

```yaml
{{ #include ../../demos/demo-token-transfers/dipdup.yml }}
```

Callback receives `TzktTokenTransferData` model that optionally contains the transfer sender, receiver, amount, and token metadata.

```python
{{ #include ../../demos/demo-token-transfers/src/demo_token_transfers/handlers/on_token_transfer.py }}
```
