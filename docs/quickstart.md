# Quickstart

This page will guide you through the steps to get your first selective indexer up and running in a few minutes without getting too deep into the details.

Let's create an indexer for the [tzBTC FA1.2 token contract](https://tzkt.io/KT1PWx2mnDueood7fEmfbBDKx1D9BAnnXitn/operations/). Our goal is to save all token transfers to the database and then calculate some statistics of its holders' activity.

A modern Linux/macOS distribution with Python 3.10 installed is required to run DipDup.

## Create a new project

### Interactively (recommended)

You can initialize a hello-world project interactively by choosing configuration options in the terminal. The following command will install DipDup for the current user:

```shell
python -c "$(curl -sSL https://dipdup.io/install.py)"
```

Now, let's create a new project:

```shell
dipdup new
```

Follow the instructions; the project will be created in the current directory. You can skip reading the rest of this page and slap `dipdup run` instead.

### From scratch

Currently, we mainly use [Poetry](https://python-poetry.org) for dependency management in DipDup. If you prefer hatch, pdb, piptools or others — use them instead. Below are some snippets to get you started.

```shell
# Create a new project directory
mkdir dipdup-indexer; cd dipdup-indexer

# Plain pip
python -m venv .venv
. .venv/bin/activate
pip install dipdup

# or Poetry
poetry init --python ">=3.10,<3.11"
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
{{ #include ../demos/demo-tzbtc/dipdup.yml }}
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
{{ #include ../demos/demo-tzbtc/src/demo_tzbtc/models.py }}
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
{{ #include ../demos/demo-tzbtc/src/demo_tzbtc/handlers/on_balance_update.py }}
```

Three methods of tzBTC contract can alter token balances — `transfer`, `mint`, and `burn`. The last one is omitted in this tutorial for simplicity. Edit corresponding handlers to call the `on_balance_update` method with data from matched operations:

`on_transfer.py`

```python
{{ #include ../demos/demo-tzbtc/src/demo_tzbtc/handlers/on_transfer.py }}
```

`on_mint.py`

```python
{{ #include ../demos/demo-tzbtc/src/demo_tzbtc/handlers/on_mint.py }}
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
