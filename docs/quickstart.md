# Quickstart

This page will guide you through the steps to get your first selective indexer up and running in a few minutes without getting too deep into the details.

Let's create an indexer for the [tzBTC FA1.2 token contract](https://tzkt.io/KT1PWx2mnDueood7fEmfbBDKx1D9BAnnXitn/operations/). Our goal is to save all token transfers to the database and then calculate some statistics of its holders' activity.

A Linux environment with Python 3.10 installed is required to use DipDup.

## Create a new project

### From template

Cookiecutter is a cool `jinja2` wrapper to initialize hello-world templates of various frameworks and toolkits interactively. Install `python-cookiecutter` package systemwide, then call:

```shell
cookiecutter https://github.com/dipdup-net/cookiecutter-dipdup
```

### From scratch

We advise using the `poetry` package manager for new projects.

```shell
poetry init
poetry add dipdup
poetry shell
```

> 💡 **SEE ALSO**
>
> * {{ #summary getting-started/installation.md}}
> * [Poetry documentation](https://python-poetry.org/docs/)

## Write a configuration file

DipDup configuration is stored in YAML files of a specific format. Create a new file named `dipdup.yml` in your current working directory with the following content:

```yaml
{{ #include ../src/demo_tzbtc/dipdup.yml }}
```

> 💡 **SEE ALSO**
>
> * {{ #summary getting-started/templates-and-variables.md}}
> * {{ #summary config/README.md}}

## Initialize project tree

Now it's time to generate typeclasses and callback stubs. Run the following command:

```shell
dipdup init
```

DipDup will create a Python package `demo_tzbtc` having the following structure:

```text
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
│   ├── on_index_rollback.py
│   └── on_synchronized.py
├── __init__.py
├── models.py
├── sql
│   ├── on_reindex
│   ├── on_restart
│   ├── on_index_rollback
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

That's a lot of files and directories! But don't worry, we will need only `models.py` and `handlers` modules in this guide.

> 💡 **SEE ALSO**
>
> * {{ #summary getting-started/project-structure.md}}
> * {{ #summary cli-reference.md#init}}

## Define data models

Our schema will consist of a single model `Holder` having several fields:

* `address` — account address
* `balance` — in tzBTC
* `volume` — total transfer/mint amount bypassed
* `tx_count` — number of transfers/mints
* `last_seen` — time of the last transfer/mint

Put the following content in the `models.py` file:

```python
from tortoise import Model, fields


class Holder(Model):
    address = fields.CharField(max_length=36, pk=True)
    balance = fields.DecimalField(decimal_places=8, max_digits=20, default=0)
    volume = fields.DecimalField(decimal_places=8, max_digits=20, default=0)
    tx_count = fields.BigIntField(default=0)
    last_seen = fields.DatetimeField(null=True)
```

> 💡 **SEE ALSO**
>
> * {{ #summary getting-started/defining-models.md}}
> * [Tortoise ORM documentation](https://tortoise-orm.readthedocs.io/en/latest/)
> * [Tortoise ORM examples](https://tortoise-orm.readthedocs.io/en/latest/examples.html)

## Implement handlers

Everything's ready to implement an actual indexer logic.

Our task is to index all the balance updates, so we'll start with a helper method to handle them. Create a file named `on_balance_update.py` in the `handlers` package with the following content:

```python
{{ #include ../src/demo_tzbtc/handlers/on_balance_update.py }}
```

Three methods of tzBTC contract can alter token balances — `transfer`, `mint`, and `burn`. The last one is omitted in this tutorial for simplicity. Edit corresponding handlers to call the `on_balance_update` method with data from matched operations:

`on_transfer.py`

```python
{{ #include ../src/demo_tzbtc/handlers/on_transfer.py }}
```

`on_mint.py`

```python
{{ #include ../src/demo_tzbtc/handlers/on_mint.py }}
```

And that's all! We can run the indexer now.

> 💡 **SEE ALSO**
>
> * {{ #summary getting-started/implementing-handlers.md}}

## Run your indexer

```shell
dipdup run
```

DipDup will fetch all the historical data and then switch to realtime updates. Your application data has been successfully indexed!

> 💡 **SEE ALSO**
>
> * {{ #summary cli-reference.md}}
