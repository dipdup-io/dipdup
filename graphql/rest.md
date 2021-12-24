# REST endpoints

Hasura 2.0 introduced the ability to expose arbitrary GraphQL queries as REST endpoints. By default, DipDup will generate GET and POST endpoints to fetch rows by primary key for all tables:

```shell
curl http://127.0.0.1:8080/api/rest/hicEtNuncHolder?address=tz1UBZUkXpKGhYsP5KtzDNqLLchwF4uHrGjw
{
  "hicEtNuncHolderByPk": {
    "address": "tz1UBZUkXpKGhYsP5KtzDNqLLchwF4uHrGjw"
  }
}
```

However, there's a limitation dictated by how Hasura parses HTTP requests: only models with primary keys of basic types (int, string, and so on) can be fetched with GET requests. An attempt to fetch model with BIGINT primary key will lead to the error: `Expected bigint for variable id got Number`.
A workaround to fetching any model is to send a POST request containing a JSON payload with a single key:

```shell
curl -d '{"id": 152}' http://127.0.0.1:8080/api/rest/hicEtNuncToken
{
  "hicEtNuncTokenByPk": {
    "creatorId": "tz1UBZUkXpKGhYsP5KtzDNqLLchwF4uHrGjw",
    "id": 152,
    "level": 1365242,
    "supply": 1,
    "timestamp": "2021-03-01T03:39:21+00:00"
  }
}
```

We hope to get rid of this limitation someday and will let you know as soon as it happens.

## Custom endpoints

You can put any number of `.graphql` files into `graphql` directory in your project's root, and DipDup will create REST endpoints for each of those queries. Let's say we want to fetch not only a specific token, but also the number of all tokens minted by its creator:

```graphql
query token_and_mint_count($id: bigint) {
  hicEtNuncToken(where: {id: {_eq: $id}}) {
    creator {
      address
      tokens_aggregate {
        aggregate {
          count
        }
      }
    }
    id
    level
    supply
    timestamp
  }
}
```

Save this query as `graphql/token_and_mint_count.graphql` and run `dipdup configure-hasura`. Now, this query is available via REST endpoint at `http://127.0.0.1:8080/api/rest/token_and_mint_count`.

You can disable exposing of REST endpoints in the config:

```yaml
hasura:
  rest: False
```
