---
description: Inventory block
---

# contracts

This is a list of the contract addresses that you might use in the indexer patterns or templates. Each contract entry has two fields:

* `address` — either originated or implicit account address, Base58 encoded.
* `typename` — an alias for the particular contract script, meaning that two contracts sharing the same code must have the same type name.

{% hint style="info" %}
Type name is required when you are using index templates to ensure type consistency, but it's recommended to always set this field to improve auto-generated code readability.
{% endhint %}

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

**NOTE** that contract entry is basically an alias for the address, there's no mention of the network, thus it's a good practice to add network name to the contract alias. The reason for this design choice is to provide a generic index parameterization via the single mechanism — [templates](templates.md).

