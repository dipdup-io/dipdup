# hasura

This optional section used by DipDup executor to automatically configure Hasura engine to track your tables.

```yaml
hasura:
  url: http://hasura:8080
  admin_secret: ${HASURA_ADMIN_SECRET:-changeme}
  allow_aggregations: false
  camel_case: true
  rest: true
  select_limit: 100
  source: default
```

> 💡 **SEE ALSO**
>
> * {{ #summary graphql/hasura.md}}
> * {{ #summary cli-reference.md#dipdup-hasura-configure}}
