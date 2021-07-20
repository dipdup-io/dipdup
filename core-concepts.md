# Core concepts

DipDup is a tool that abstracts developer from the indexing and data serving workflow and let him focus on the business logic only. It also applies selective indexing techniques to ensure fast initial sync phase and the most efficient use of public API endpoints.

## Big picture

DipDup is heavily inspired by [The Graph](https://thegraph.com/) Protocol but there are several important differences:

* DipDup works with operation groups \(explicit operation and all internal ones\) and _Big\_map_ updates \(lazy hash map structures\) — until fully-fledged events are implemented in Tezos.
* DipDup utilizes microservice approach and relies heavily on existing solutions which makes the SDK itself very lightweight and does not limit developer with a single programming language or a particular API engine.

{% hint style="info" %}
You can think of DipDup as a set of best practices for building custom backends for decentralized applications plus a toolkit that spares you from writing boilerplate code.
{% endhint %}

DipDup is currently tightly coupled with [TzKT API](http://api.tzkt.io/) but generally can use any data provider that implements a particular feature set. TzKT provides REST endpoints and Websocket subscriptions with flexible filters enabling selective indexing, and returns "humanified" contract data, which means that you don't have to handle raw Michelson expressions.

While you are free to use any database and API engine \(e.g. write your own API backend\), by default DipDup offers PostgreSQL + Hasura GraphQL combo that takes care of exposing indexed data and works out of the box with minimal configuration.

![Default DipDup setup and data flow](.gitbook/assets/dipdup.svg)

## How it works

From the developer perspective there are three main steps for creating an indexer using DipDup framework:

1. Write a declarative configuration file containing all the inventory and indexing rules
2. Describe your domain-specific data models
3. Implement the business logic which is basically how to convert blockchain data to your models

In the result you get a service responsible for filling the database with the indexed data.

Within this service there can be multiple indexers running independently

## Atomicity and persistency

Here's a few important things to know before running your indexer:

* Make sure that database you're connecting to is used by DipDup exclusively. When index configuration or models change the whole **database will be dropped** and indexing will start from scratch.
* Do not rename existing indexes in config file without cleaning up the database first, DipDup won't be able to handle that automatically and will treat the renamed index as a new one.
* Multiple indexes pointing to different contracts should not reuse the same models \(unless you know what you are doing\) because synchronization is done sequentially index by index.
* Reorg messages signal about chain reorganizations, when some blocks, including all operations, are rolled back in favor of blocks with higher fitness. Chain reorgs happen from time to time \(especially in testnets\), so it's not something you can ignore. You have to handle such messages correctly, otherwise you will likely accumulate duplicate data or, worse, invalid data. You can implement your own rollback logic by editing auto-generated `on_rollback` handler.

### Single level reorgs

It's important for DipDup to be able to handle chain reorgs since reindexing from scratch leads to several minutes of downtime. Single level rollbacks are now processed in the following way:

* If the new block has the same subset of operations as the replaced one — do nothing;
* If the new block has all the operation from the replaced one AND several new operations — process those new operations;
* If the new block misses some operations from the replaced one: trigger full reindexing.

