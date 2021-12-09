# Quickstart

This page will guide you through the steps to get your first selective indexer up and running in a few minutes without getting too deep into the details.

Let's create an indexer for [tzBTC FA1.2 token contract](https://tzkt.io/KT1PWx2mnDueood7fEmfbBDKx1D9BAnnXitn/operations/). Our goal is to save all token transfers to the database, then calculate some statistics of its' holders' activity.

## Install framework

A Linux environment with Python 3.8+ installed is required to use DipDup.

### poetry (recommended)

```shell
poetry init -n
poetry add dipdup
```

### pip

```shell
python -m venv .venv
source .venv/bin/activate
pip install dipdup
```

See [Installation](getting-started/installation.md) section for details.

## Write a configuration file

Create a new file named `dipdup.yml` in your current working directory with the following content:

```yaml
spec_version: 1.2
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

See [Config reference](config-reference) section for details.

## Initialize project tree

Now it's time to generate typeclasses and callback stubs. Run the following command:

```shell
dipdup init
```

DipDup will create a Python package `demo_tzbtc` having the following structure:

{% tabs %}
{% tab title="Python" %}

```
demo_tzbtc
├── graphql
├── handlers
│   ├── __init__.py
│   ├── on_mint.py
│   └── on_transfer.py
├── hooks
│   ├── __init__.py
│   ├── on_reindex.py
│   ├── on_restart.py
│   ├── on_rollback.py
│   └── on_synchronized.py
├── __init__.py
├── models.py
├── sql
│   ├── on_reindex
│   ├── on_restart
│   ├── on_rollback
│   └── on_synchronized
└── types
    ├── __init__.py
    └── tzbtc
        ├── __init__.py
        ├── parameter
        │   ├── __init__.py
        │   ├── mint.py
        │   └── transfer.py
        └── storage.py
```

{% endtab %}
{% endtabs %}

That's a lot of files and directories! But don't worry, for this guide, we will need only `models.py` module and `handlers` package.

See [Project structure](getting-started/project-structure) section for details.

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
    holder.turnover += abs(balance_update)
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

```python#indent=4
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
        # NOTE: Internal tzBTC transaction
        return

    amount = Decimal(transfer.parameter.value) / (10 ** 8)
    await on_balance_update(
        address=transfer.parameter.from_,
        balance_update=-amount,
        timestamp=transfer.data.timestamp,
    )
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

DipDup will fetch all the historical data then switch to real-time updates. Your application data has been successfully indexed!
