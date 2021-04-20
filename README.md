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

Check that DipDup CLI has been successfully installed:

```text
dipdup --version
```

## Write config file

Create `dipdup.yml` file in your project. Here are the two required fields your configuration has to start with:

```yaml
spec_version: 0.0.1
package: atomex
```

### Database connection

In this tutorial we will use the simplest DB engine supported — SQLite:

```yaml
database:
  kind: sqlite
  path: atomex.sqlite3
```

### Contract address

We will work with a single-contract dapp, and only with it's mainnet deployment:

```yaml
contracts:
  atomex_mainnet:
    address: KT1VG2WtYdSWz5E7chTeAdDPZNy2MpP8pTfL
    typename: atomex
```

### Data provider

DipDup currently supports only [TzKT ](http://api.tzkt.io/)data provider.

```yaml
datasources:
  tzkt_staging:
    kind: tzkt
    url: https://staging.api.tzkt.io
```

### Index patterns

We want to

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
```

## Generate types

```text
dipdup init
```



## Define data models

{% tabs %}
{% tab title="Python" %}

{% endtab %}
{% endtabs %}

## Implement handlers

{% tabs %}
{% tab title="Python" %}

{% endtab %}
{% endtabs %}

## Run your indexer

```text
dipdup run
```

