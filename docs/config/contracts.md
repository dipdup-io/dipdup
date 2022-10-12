# contracts

A list of the contracts you can use in the index definitions. Each contract entry has two fields:

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

If the `typename` field is not set, a contract alias will be used instead.

Contract entry does not contain information about the network, so it's a good idea to include the network name in the alias. This design choice makes possible a generic index parameterization via templates. See {{ #summary getting-started/templates-and-variables.md }} for details.

If multiple contracts you index have the same interface but different code, see {{ #summary faq.md }} to learn how to avoid conflicts.
