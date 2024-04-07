# DipDup

This page will guide you through the steps to get your first DipDup indexer up and running in a few minutes without getting too deep into the details.

Let's create an indexer for output transactions from a specific address. We will need to set up the indexing environment, configure the indexer, and store the results in a database.

## Prerequisites

Before starting with DipDup, make sure you have the right tools and knowledge:

- **Operating System**: You'll need a modern Linux/macOS distribution.
- **Python Version**: Python 3.11 is required for DipDup. You can check your Python version by running `python3 --version` in your terminal.
- **Knowledge Base**: Being familiar with Python programming is essential for working with DipDup.

## Understanding DipDup

DipDup is a framework that makes it easier for developers to create selective indexers for decentralized applications by managing interactions with blockchain data. Its key features include a declarative configuration for indexing and Python for business logic, supporting multiple blockchain platforms and various databases like SQLite, PostgreSQL, and TimescaleDB. DipDup also provides a ready-to-use GraphQL API for data queries and a comprehensive CLI for project management. Its structure helps developers by organizing data models, business logic, and configuration settings efficiently, making the process of building blockchain applications straightforward and manageable.

## Step 1 — Install DipDup

The easiest way to install DipDup as a CLI application [pipx](https://pipx.pypa.io/stable/). We have a convenient wrapper script that installs DipDup for the current user. Run the following command in your terminal:

```shell [Terminal]
curl -Lsf https://dipdup.io/install.py | python3
```

See the [Installation](https://dipdup.io/docs/installation) page for all options.

## Step 2 — Create a project

DipDup CLI has a built-in project generator. Run the following command in your terminal:

```shell [Terminal]
dipdup new
```

For educational purposes, we'll create a project from scratch, so choose `[none]` network and `demo_blank` template.

Follow the instructions; the project will be created in the new directory.

## Step 3 — Configuration file

In the project root, you'll find a file named `dipdup.yaml`. It's the main configuration file of your indexer. We will discuss it in detail in the [Config](https://dipdup.io/docs/getting-started/config) section; for now just replace its content with the following:

```yaml [dipdup.yaml]
{{ #include kakarot_key_files/dipdup.yaml }}
```

Now it's time to generate project structure, run the following command, it will generate callbacks and other entities we defined in configuration, don't worry in this guide we will only need a small portion of those:

```shell [Terminal]
dipdup init
```

Read more about project structure: <https://dipdup.io/docs/getting-started/package>

## Step 4 — Define data models and implement handlers

In this step we will define the business logic of our application.
DipDup supports storing data in SQLite, PostgreSQL and TimescaleDB databases. We use custom ORM based on Tortoise ORM as an abstraction layer.

First, you need to define a model class. Our schema will consist of a single model `Transaction` model:

```python [models/__init__.py]
{{ #include kakarot_key_files/__init__.py }}
```

Now it's time to connect everything together with the handler `on_output_transaction` which was stated in configuration:

```python [handlers/on_output_transaction.py]
{{ #include kakarot_key_files/on_output_transaction.py }}
```

## Step 5 — Results

Run the indexer, will right data to sqlite defined in configuration:

```shell
dipdup run
```

DipDup will fetch all the historical data. You can check the progress in the logs.

Run this query to check the data:

```bash
sqlite3 /tmp/kakarot.sqlite 'SELECT * FROM transaction LIMIT 10'
```

## Explore DipDup

To dive deeper into DipDup and unlock its full potential, visit the [official DipDup documentation](https://dipdup.io/docs). The documentation offers a thorough exploration of the framework, from installation steps to detailed examples and complex demo projects. It’s designed to assist developers at every step, ensuring an efficient development process for both simple indexers and sophisticated blockchain applications.
