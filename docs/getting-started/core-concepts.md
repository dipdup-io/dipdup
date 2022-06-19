# Core concepts

## Big picture

DipDup is heavily inspired by [The Graph](https://thegraph.com/) Protocol, but there are several differences:

* DipDup works with operation groups (explicit operation and all internal ones) and _Big\_map_ updates (lazy hash map structures) — until fully-fledged events are implemented in Tezos.
* DipDup utilizes a microservice approach and relies heavily on existing solutions, making the SDK very lightweight and allowing it to switch API engines on demand.

Consider DipDup a set of best practices for building custom backends for decentralized applications, plus a toolkit that spares you from writing boilerplate code.

DipDup is tightly coupled with [TzKT API](http://api.tzkt.io/) but can generally use any data provider which implements a particular feature set. TzKT provides REST endpoints and Websocket subscriptions with flexible filters enabling selective indexing and returns "humanified" contract data, which means you don't have to handle raw Michelson expressions.

DipDup offers PostgreSQL + Hasura GraphQL Engine combo out-of-the-box to expose indexed data via REST and GraphQL with minimal configuration. However, you can use any database and API engine (e.g., write your own API backend).

![Default DipDup setup and data flow](../assets/dipdup.svg)

## How it works

From the developer's perspective, there are three main steps for creating an indexer using DipDup framework:

1. Write a declarative configuration file containing all the inventory and indexing rules.
2. Describe your domain-specific data models.
3. Implement the business logic, which is how to convert blockchain data to your models.

As a result, you get a service responsible for filling the database with the indexed data.

Within this service, there can be multiple indexers running independently.

## Atomicity and persistency

DipDup applies all updates atomically block by block. In case of an emergency shutdown, it can safely recover later and continue from the level it ended. DipDup state is stored in the database per index and can be used by API consumers to determine the current indexer head.

Here are a few essential things to know before running your indexer:

* Ensure that the database you're connecting to is used by DipDup exclusively. Changes in index configuration or models require DipDup to **drop the whole database** and start indexing from scratch.
* Do not rename existing indexes in the config file without cleaning up the database first. DipDup won't handle that automatically and will treat the renamed index as new.
* Multiple indexes pointing to different contracts should not reuse the same models (unless you know what you are doing) because synchronization is done sequentially by index.

## Schema migration

DipDup does not support database schema migration: if there's any model change, it will trigger reindexing. The rationale is that it's easier and faster to start over than handle migrations that can be of arbitrary complexity and do not guarantee data consistency.

DipDup stores a hash of the SQL version of the DB schema and checks for changes each time you run indexing.

## Handling chain reorgs

Reorg messages signaling chain reorganizations. That means some blocks, including all operations, are rolled back in favor of another with higher fitness. Chain reorgs happen regularly (especially in testnets), so it's not something you can ignore. You must handle such messages correctly - otherwise, you will likely accumulate duplicate or invalid data. You can implement your rollback logic by editing the `on_index_rollback` hook.

### Single level

Single level rollbacks are processed in the following way:

* If the new block has the same subset of operations as the replaced one — do nothing;
* If the new block has all the operations from the replaced one AND several new operations — process those new operations;
* If the new block misses some operations from the replaced one: trigger full reindexing.
