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

Make a new folder and create a configuration file `dipdup.yml` inside with the following content:

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
  tzkt_mainnet:
    kind: tzkt
    url: https://api.tzkt.io
    
indexes:
  tzbtc_holders_mainnet:
    kind: operation
    datasource: tzkt_mainnet
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

We will index all the tzBTC transfers and mints and store indexed data in the models representing token holders.

## Generate types

```text
dipdup init
```

This command will generate the following files:

{% tabs %}
{% tab title="Python" %}
```text
demo_tzbtc/
├── models.py
├── handlers
│   ├── on_transfer.py
│   ├── on_mint.py
│   ├── on_configure.py
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
    last_seen = fields.DatetimeField(null=True)
```
{% endtab %}
{% endtabs %}

## Implement handlers

Our task is to properly index all the balance updates, so we'll start with a helper method handling them.

{% tabs %}
{% tab title="Python" %}
`on_balance_update.py`

```python
from decimal import Decimal
import demo_tzbtc.models as models


async def on_balance_update(
    address: str,
    balance_update: Decimal, 
    timestamp: str
) -> None:
    holder, _ = await models.Holder.get_or_create(address=address)
    holder.balance += balance_update
    holder.tx_count += 1
    holder.last_seen = timestamp
    assert holder.balance >= 0, address
    await holder.save()
```
{% endtab %}
{% endtabs %}

That was pretty straightforward👍🏻

Now we need to handle two contract methods that can alter token balances — `transfer` and `mint` \(there's also `burn`, but for simplicity we'll omit that in this tutorial\).

{% tabs %}
{% tab title="Python" %}
`on_transfer.py`

```python
from typing import Optional
from decimal import Decimal

from dipdup.models import Transaction
from dipdup.context import HandlerContext

import demo_tzbtc.models as models

from demo_tzbtc.types.tzbtc.parameter.transfer import TransferParameter
from demo_tzbtc.types.tzbtc.storage import TzbtcStorage
from demo_tzbtc.handlers.on_balance_update import on_balance_update


async def on_transfer(
    ctx: HandlerContext,
    transfer: Transaction[TransferParameter, TzbtcStorage],
) -> None:
    if transfer.parameter.from_ == transfer.parameter.to:
        return  # tzBTC specific
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

from dipdup.models import Transaction
from dipdup.context import HandlerContext

import demo_tzbtc.models as models

from demo_tzbtc.types.tzbtc.parameter.mint import MintParameter
from demo_tzbtc.types.tzbtc.storage import TzbtcStorage
from demo_tzbtc.handlers.on_balance_update import on_balance_update


async def on_mint(
    ctx: HandlerContext,
    mint: Transaction[MintParameter, TzbtcStorage],
) -> None:
    amount = Decimal(mint.parameter.value) / (10 ** 8)
    await on_balance_update(address=mint.parameter.to,
                            balance_update=amount,
                            timestamp=mint.data.timestamp)

```
{% endtab %}
{% endtabs %}

And that's all! We can run the indexer now.

## Run your indexer

```text
dipdup run
```

DipDup will fetch all the historical data first, and then switch to real-time updates. You application data has been successfully indexed!

