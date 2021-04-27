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
  tzbtc_mainnet:
    address: KT1PWx2mnDueood7fEmfbBDKx1D9BAnnXitn
    typename: tzbtc

datasources:
  tzkt_staging:
    kind: tzkt
    url: https://staging.api.tzkt.io
    
indexes:
  tzbtc_holders_mainnet:
    kind: operation
    datasource: tzkt_staging
    contract: tzbtc_mainnet
    handlers:
      - callback: on_transfer
        pattern:
          - destination: tzbtc_mainnet
            entrypoint: transfer
      - callback: on_mint
        pattern:
          - destination: tzbtc_mainnet
            entrypoint: mint
```

We will index all the tzBTC transfers and mints and have stateful models representing token holders.

## Generate types

```text
dipdup init
```

This command will generate the following files:

{% tabs %}
{% tab title="Python" %}
```text
dipdup_demo/
├── models.py
├── handlers
│   ├── on_transfer.py
│   ├── on_mint.py
│   └── on_rollback.py
└── types
    └── tzbtc
        ├── storage
        └── parameter
            └── transfer.py
            └── mint.py
```
{% endtab %}
{% endtabs %}

Let's fill them one by one.

## Define data models

Our schema will consist of a single model `Holder` having several fields:

* `address` — account address
* `balance` — in tzBTC
* `volume` — total transfer/mint amount bypassed
* `tx_count` — number of transfers/mints
* `last_seen` — time of the last transfer/mint

{% tabs %}
{% tab title="Python" %}
```python
from tortoise import Model, fields


class Holder(Model):
    address = fields.CharField(max_length=36, pk=True)
    balance = fields.DecimalField(decimal_places=6, max_digits=20, default=0)
    volume = fields.DecimalField(decimal_places=6, max_digits=20, default=0)
    tx_count = fields.BigIntField(default=0)
    last_seen = fields.DateTimeField(null=True)
```
{% endtab %}
{% endtabs %}

## Implement handlers



{% tabs %}
{% tab title="Python" %}
`on_transfer.py`

```python
from dipdup_demo.types.tzbtc.parameter.transfer import Transfer
import dipdup_demo.models as models
from dipdup.models import HandlerContext, OperationContext


async def on_transfer(
    ctx: HandlerContext, 
    transfer: OperationContext[Transfer]
) -> None:
    
    sender = await 
    
```

`on_mint.py`

```python

```
{% endtab %}
{% endtabs %}



## Run your indexer

```text
dipdup run
```



