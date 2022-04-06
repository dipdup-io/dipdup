# hasura

This optional section used by DipDup executor to automatically configure Hasura engine to track your tables.

```yaml
hasura:
  url: http://hasura:8080
  admin_secret: ${HASURA_ADMIN_SECRET:-changeme}
```

> 🤓 **SEE ALSO**
>
> * [6.1. Hasura integration](../../advanced/config/datasources.md)
> * [13.5. hasura configure](../../cli/hasura-configure.md)