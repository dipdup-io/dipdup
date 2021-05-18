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
package: demo_tzbtc

database:
  kind: sqlite
  path: demo_tzbtc.sqlite3
  
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
    contracts: 
      - tzbtc_mainnet
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
        ├── storage.py
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
    balance = fields.DecimalField(decimal_places=8, max_digits=20, default=0)
    volume = fields.DecimalField(decimal_places=8, max_digits=20, default=0)
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
from typing import Optional
from decimal import Decimal

from dipdup.models import OperationData, OperationHandlerContext, 
    OriginationContext, TransactionContext

import demo_tzbtc.models as models

from demo_tzbtc.types.tzbtc.parameter.transfer import TransferParameter
from demo_tzbtc.types.tzbtc.storage import TzbtcStorage
from demo_tzbtc.handlers.on_balance_update import on_balance_update


async def on_transfer(
    ctx: OperationHandlerContext,
    transfer: TransactionContext[TransferParameter, TzbtcStorage],
) -> None:
    if transfer.parameter.from_ == transfer.parameter.to:
        return
    amount = Decimal(transfer.parameter.value) / (10 ** 8)
    await on_balance_update(address=transfer.parameter.from_,
                            balance_update=-amount,
                            timestamp=transfer.data.timestamp)
    await on_balance_update(address=transfer.parameter.to,
                            balance_update=amount,
                            timestamp=transfer.data.timestamp)
```

`on_mint.py`

```python
from typing import Optional
from decimal import Decimal

from dipdup.models import OperationData, OperationHandlerContext, 
    OriginationContext, TransactionContext

import demo_tzbtc.models as models

from demo_tzbtc.types.tzbtc.parameter.mint import MintParameter
from demo_tzbtc.types.tzbtc.storage import TzbtcStorage
from demo_tzbtc.handlers.on_balance_update import on_balance_update


async def on_mint(
    ctx: OperationHandlerContext,
    mint: TransactionContext[MintParameter, TzbtcStorage],
) -> None:
    amount = Decimal(mint.parameter.value) / (10 ** 8)
    await on_balance_update(address=mint.parameter.to,
                            balance_update=amount,
                            timestamp=mint.data.timestamp)

```
{% endtab %}
{% endtabs %}



## Run your indexer

```text
dipdup run
```



