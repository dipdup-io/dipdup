# DipDup

This page will guide you through the steps to get your first DipDup indexer up and running in a few minutes without getting too deep into the details.

Let's create an indexer to track balances of particular token. We will need to set up the indexing environment, configure the indexer, and store the results in a database.

## Prerequisites

Here are a few things you need to get started with DipDup:

- **Skills**: Basic Python 3 knowledge to implement data handlers.
- **Operating System**: You can use any Linux/macOS distribution on amd64/arm64 platforms with Python installed.
- **Python Version**: Python 3.11 is required for DipDup. You can check your Python version by running `python3 --version` in your terminal.

## Understanding DipDup

DipDup is a software framework that helps web3 developers create selective indexers for decentralized applications. It uses blockchain data provided by various off-chain data sources. Some of the key features of DipDup include:

- **Ready For Multichain**: DipDup supports dozens of blockchains, and we are constantly adding new ones. You can easily reuse your business logic for different networks or even index multiple chains in a single project.
- **Declarative Configuration**: A whole indexer is defined by a single configuration file and a bunch of Python data handlers. Code is completely separated from the configuration and environment variables, making it easy to maintain and deploy your project.
- **Lots of Integrations**: You can use SQLite, PostgreSQL, or TimescaleDB databases to store blockchain data, deploy to Compose or Swarm with a single command, monitor your indexer with Prometheus or Sentry, and more.
- **Magic GraphQL API**: DipDup automatically generates a GraphQL API for your data using Hasura, so you can easily query it from your frontend or other services. You can easily extend API with custom queries and metadata requests.
- **Powerful CLI**: DipDup CLI has everything you need to manage your project, from creating a new one to running and deploying. And it's very convenient. There are lots of templates for various blockchains and use cases, so you can start quickly.

## Step 1 — Install DipDup

The easiest way to install DipDup as a CLI application is [pipx](https://pipx.pypa.io/stable/) with `pipx install dipdup` command. If you don't want to deal with tooling, we have a convenient installer script. Run the following command in your terminal:

```shell [Terminal]
curl -Lsf https://dipdup.io/install.py | python3
```

See the [Installation](https://dipdup.io/docs/installation) page for other options.

## Step 2 — Create a project

DipDup CLI has a built-in project generator. Run the following command in your terminal:

```shell [Terminal]
dipdup new
```

In this guide we will use one of our demos - demo_evm_events as a template:
![Terminal output of `dipdup new` command](zksync_assets/dipdupnew.png)

Dipdup will generate complete project structure, including USDT balances tracking logic, which is implemented in demo. Let's look further into it in following steps.

## Step 3 — Configuration file

In the project root, you'll find a file named `dipdup.yaml`. It's the main configuration file of your indexer. We will discuss it in detail in the [Config](1.getting-started/3.config.md) section; for now just replace contract address with target token, I will use zkSync USDT for this example:

```yaml [dipdup.yaml]
{{ #include foreign/zksync_files/dipdup.yaml }}
```

## Step 4 — Implement handlers

  TODO
Implement handlers from quickstart with an ORM explanation (models were implemented in the demo, check {link to docs}).
Key steps: check out handlers, explain below about orm and generated models

```yaml [on_transfer.py]
{{ #include foreign/zksync_files/on_transfer.py }}
```

## Step 5 — Run

  To copy from kakarot
Shorter "Next steps" from quickstart
Key steps: how to up compose stack from generated project using env

### Fancy query

Demonstrate a Hasura request from the docker-compose stack
Key steps: how to up compose stack from generated project, show query in hasura web interface

## Explore DipDup

To learn more about DipDup features, visit the [official DipDup documentation](https://dipdup.io/docs). It offers an in-depth explanation of the framework concepts, lots of examples from basic to the most advanced, allowing rapid and efficient development of blockchain data indexers of any complexity.
