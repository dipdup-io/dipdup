---
description: Get your selective indexer up & running in a few steps
---

# Quick start

## Install SDK

{% tabs %}
{% tab title="Python" %}
```bash
pip install dipdup
```
{% endtab %}
{% endtabs %}

## Write config file

Make new folder named `dipdup_demo` cd in and create a configuration file `dipdup.yml` with the following content:

```yaml
spec_version: 0.1
package: dipdup_demo

database:
  kind: sqlite
  path: demo.sqlite3
  
contracts:

datasources:
  tzkt_staging:
    kind: tzkt
    url: https://staging.api.tzkt.io
    
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



