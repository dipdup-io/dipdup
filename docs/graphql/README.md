# GraphQL API

In this section, we assume you use Hasura GraphQL Engine integration to power your API.

Before starting to do client integration, it's good to know the specifics of Hasura GraphQL protocol implementation and the general state of the GQL ecosystem.

## Queries

By default, Hasura generates three types of queries for each table in your schema:

* Generic query enabling filters by all columns
* Single item query (by primary key)
* Aggregation query (can be disabled in config)

All the GQL features such as fragments, variables, aliases, directives are supported, as well as batching.  
Read more in [Hasura docs](https://hasura.io/docs/latest/graphql/core/databases/postgres/queries/index.html).

It's important to understand that a GraphQL query is just a [POST request](https://graphql.org/graphql-js/graphql-clients/) with JSON payload, and in some instances, you don't need a complicated library to talk to your backend.

### Pagination

By default, Hasura does not restrict the number of rows returned per request, which could lead to abuses and a heavy load on your server. You can set up limits in the configuration file. See {{ #summary config/hasura.md#limit-number-of-rows }}. But then, you will face the need to [paginate](https://hasura.io/docs/latest/graphql/core/databases/postgres/queries/pagination.html) over the items if the response does not fit the limits.

## Subscriptions

From [Hasura documentation](https://hasura.io/docs/latest/graphql/core/databases/postgres/subscriptions/index.html):

Hasura GraphQL engine subscriptions are **live queries**, i.e., a subscription will return the latest result of the query and not necessarily all the individual events leading up to it.

This feature is essential to avoid complex state management (merging query results and subscription feed). In most scenarios, live queries are what you need to sync the latest changes from the backend.

> ⚠ **WARNING**
>
> If the live query has a significant response size that does not fit into the limits, you need one of the following:
>
> 1. Paginate with offset (which is not convenient)
> 2. Use cursor-based pagination (e.g., by an increasing unique id).
> 3. Narrow down request scope with filtering (e.g., by timestamp or level).

Ultimately you can get "subscriptions" on top of live quires by requesting all the items having ID greater than the maximum existing or all the items with a timestamp greater than now.

### Websocket transport

Hasura is compatible with [subscriptions-transport-ws](https://github.com/apollographql/subscriptions-transport-ws) library, which is currently deprecated but still used by most clients.

## Mutations

The purpose of DipDup is to create indexers, which means you can consistently reproduce the state as long as data sources are accessible. It makes your backend "stateless", meaning tolerant to data loss.

However, you might need to introduce a non-recoverable state and mix indexed and user-generated content in some cases. DipDup allows marking these UGC tables "immune", protecting them from being wiped. In addition to that, you will need to set up [Hasura Auth](https://hasura.io/docs/latest/graphql/core/auth/index.html) and adjust write permissions for the tables (by default, they are read-only).

Lastly, you will need to execute GQL mutations to modify the state from the client side. [Read more](https://hasura.io/docs/latest/graphql/core/databases/postgres/mutations/index.html) about how to do that with Hasura.
