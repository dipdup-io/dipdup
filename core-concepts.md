# Core concepts

DipDup is a tool that abstracts developer from the indexing and API creation workflow and let him focus on the business logic only. It also applies selective indexing techniques to ensure fast initial sync phase and the most efficient use of public API endpoints.

DipDup is heavily inspired by [The Graph](https://thegraph.com/) Protocol but there are several important differences:

* DipDup works with operation groups \(explicit operation and all internal ones\) and _Big\_map_ updates \(lazy hash map structures\) — until fully-fledged events are implemented in Tezos.
* DipDup utilizes microservice approach and relies heavily on existing solutions which makes the SDK itself very lightweight and does not limit developer with a single programming language or a particular API engine.

{% hint style="info" %}
You can think of DipDup as a set of best practices for building custom backends for decentralized applications plus a toolkit that spares you from writing boilerplate code.
{% endhint %}

DipDup is currently tightly coupled with [TzKT API](http://api.tzkt.io/) but generally can use any data provider that implements a particular feature set. TzKT provides REST endpoints and Websocket subscriptions with flexible filters allowing truly selective indexing, and returns "humanified" contract data, meaning that you don't have to handle raw Michelson.

While you are free to use any database and API engine \(e.g. write your own API backend\), by default DipDup offers PostgreSQL + Hasura GraphQL combo that takes care of exposing indexed data and works out of the box with minimal configuration.

![Default DipDup setup](.gitbook/assets/dipdup.svg)



