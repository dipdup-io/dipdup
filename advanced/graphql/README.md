# GraphQL API

In this section we are assuming you use Hasura GraphQL Engine integration to power your API.

Before starting to do client integration, it's good to know the specifics of Hasura GraphQL protocol implementation and general state of the GQL ecosystem.

## Queries

By default, Hasura generates three types of queries for each table in your schema:

* Generic query enabling filters by all columns
* Single item query (by primary key)
* Aggregation query (can be [disabled](../config-reference/hasura.md#disable-aggregation-queries))

All the GQL features such as fragments, variables, aliases, directives are supported, as well as batching.  
Read more in [Hasura docs](https://hasura.io/docs/latest/graphql/core/databases/postgres/queries/index.html).

It's important to understand that GQL query is just a [POST request](https://graphql.org/graphql-js/graphql-clients/) with JSON payload and in certain cases you don't need a complicated library to talk to your backend.

### Pagination

By default Hasura does not restrict the number of rows returned per request which can lead to abuses and heavy load to your server. You can set up limits using the [according section](../config-reference/hasura.md#limit-number-of-rows) in the configuration file.  
But then you will face the need to [paginate](https://hasura.io/docs/latest/graphql/core/databases/postgres/queries/pagination.html) over the items if response does not fit into the limits.

## Subscriptions

From [Hasura documentation](https://hasura.io/docs/latest/graphql/core/databases/postgres/subscriptions/index.html):

Hasura GraphQL engine subscriptions are **live queries**, i.e. a subscription will return the latest result of the query and not necessarily all the individual events leading up to the result.

This is a very important feature that allows to avoid complex state management (merging query results and subscription feed). In most scenarios live queries is exactly what you need to be able to sync latest changed from the backend.

{% hint style="warning" %}
Note that if the live query has a large response that does not fit into the [limits](../config-reference/hasura.md#limit-number-of-rows), you need to either paginate with offset (which is not convenient) or use cursor-based pagination (e.g. by an increasing unique id) or narrow down the scope with filtering (e.g. by timestamp or by level).
{% endhint %}

Ultimately you can get "subscriptions" on top of live quires by requesting all the items having id greater than the maximum existing or all the items with timestamp greater than now.

### Websocket transport

Hasura is compatible with [subscriptions-transport-ws](https://github.com/apollographql/subscriptions-transport-ws) library which is currently deprecated by still used by the majority of the clients.

## Mutations

The purpose of DipDup is to create indexers, which means you can always reproduce the state as long as data sources are accessible. This makes your backend in a sense "stateless" because it's tolerant to data loss.

However in some cases you might need to introduce a non-recoverable state and mix indexed and user-generated content. DipDup allows to mark these UGC tables "immune" which protects them from being wiped. In addition to that you will need to set up [Hasura Auth](https://hasura.io/docs/latest/graphql/core/auth/index.html) and adjust write permissions for the tables (by default they are read-only).

Lastly, in order to modify the state from the client side you will need to execute GQL mutations, [read more](https://hasura.io/docs/latest/graphql/core/databases/postgres/mutations/index.html) about how to do that with Hasura.
