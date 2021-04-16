---
description: Get your selective indexer up & running in a few steps
---

# Quick start

## Install SDK

{% tabs %}
{% tab title="Python" %}
Python 3.8+ is required.

```bash
pip install dipdup
```
{% endtab %}
{% endtabs %}

Check the installed dipdup version:

```text
dipdup --version
```

## Write config file

Make new git repository and create `dipdup.yml` file in it. Here are the two obligatory fields your configuration has to start with:

```yaml
spec_version: 0.0.1
package: atomex
```

### Database connection

DipDup supports 

```yaml
database:
  kind: sqlite
  path: atomex.sqlite3
```



### Contract address

```yaml
contracts:
  atomex_mainnet:
    address: KT1VG2WtYdSWz5E7chTeAdDPZNy2MpP8pTfL
    typename: atomex
```

### Data provider

```yaml
datasources:
  tzkt_staging:
    kind: tzkt
    url: https://staging.api.tzkt.io
```

### Index patterns

```yaml
indexes:
  atomex_swaps:
    kind: operation
    datasource: tzkt_staging
    contract: atomex_mainnet
    handlers:
      - callback: on_initiate
        pattern:
          - destination: atomex_mainnet
            entrypoint: initiate
      - callback: on_redeem
        pattern:
          - destination: atomex_mainnet
            entrypoint: redeem
      - callback: on_refund
        pattern:
          - destination: atomex_mainnet
            entrypoint: refund
```

## Generate types

```text
dipdup init
```



## Define data models



## Implement handlers



## Run your indexer

```text
dipdup run
```

