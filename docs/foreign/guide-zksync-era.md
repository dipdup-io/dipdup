# DipDup

  To copy from kakarot
Guide targets and what will be in the guide

## Prerequisites

  To copy from kakarot
Python knowledge, linux/mac, Python 3.11, Zksync RPC NODE API

## Understanding DipDup

  To copy from kakarot
Describe the framework structure, principles, key features, and advantages.
Key thoughts: declarative indexing configuration with Python business logic, multiple chains, flexible database support, a configured GraphQL API, rich CLI.

## Step 1 — Install DipDup

The easiest way to install DipDup as a CLI application [pipx](https://pipx.pypa.io/stable/). We have a convenient wrapper script that installs DipDup for the current user. Run the following command in your terminal:

```shell [Terminal]
curl -Lsf https://dipdup.io/install.py | python3
```

See the [Installation](https://dipdup.io/docs/installation) page for all options.

## Step 2 — Create a project

  TODO
Create a project from demo_event_tokens, show the process and project structure (from quickstart "Generate types and stubs").

## Step 3 — Configuration file

  TODO
Adapt the configuration file to zkSync, explain typing and abi.etherscan in a few words.
Key steps: insert the target token contract, link to docs  # maybe replace "eth" in the config?

## Step 4 — Implement handlers

  TODO
Implement handlers from quickstart with an ORM explanation (models were implemented in the demo, check {link to docs}).

## Step 5 — Results

  To copy from kakarot
Shorter "Next steps" from quickstart

## Fancy query

Demonstrate a Hasura request from the docker-compose stack
Key steps: how to up compose stack from generated project, show query in hasura web interface

## Explore DipDup

  To copy from kakarot
Docs and repository link
Explore all features at dipdup.io/docs
