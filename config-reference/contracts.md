---
description: Inventory block
---

# contracts

A list of the contract definitions you might use in the indexer patterns or templates. Each contract entry has two fields:

* `address` — either originated or implicit account address encoded in base58.
* `typename` — an alias for the particular contract script, meaning that two contracts sharing the same code can have the same type name.

```yaml
contracts:
  kusd_dex_mainnet:
    address: KT1CiSKXR68qYSxnbzjwvfeMCRburaSDonT2
    typename: quipu_fa12
  tzbtc_dex_mainnet:
    address: KT1N1wwNPqT5jGhM91GQ2ae5uY8UzFaXHMJS
    typename: quipu_fa12
  kusd_token_mainnet:
    address: KT1K9gCRgaLRFKTErYt1wVxA3Frb9FjasjTV
    typename: kusd_token
  tzbtc_token_mainnet:
    address: KT1PWx2mnDueood7fEmfbBDKx1D9BAnnXitn
    typename: tzbtc_token
```

A `typename` field is only required when using index templates, but it helps to improve the readability of auto-generated code.

Contract entry does not contain information about the network, so it's a good idea to include the network name in the alias. This design choice makes possible a generic index parameterization via templates. See [Templates and variables](templates-and-variables) section for details.
