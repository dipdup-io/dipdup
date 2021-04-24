---
description: Deployment block
---

# hasura

This is an optional section used by DipDup executor to automatically configure Hasura engine to track your tables.

```yaml
hasura:
  url: http://hasura:8080
  admin_secret: ${HASURA_ADMIN_SECRET:-changeme}
```

Under the hood DipDup generates Hasura metadata file out from your DB schema and accesses Hasura instance using [admin API](https://hasura.io/docs/latest/graphql/core/api-reference/metadata-api/index.html) endpoint.

Metadata configuration is idempotent: each time you do `dipdup run` it queries the existing schema and do the merge if required.

### Authentication

DipDup sets READ only permissions for all tables and enables non-authorized access to the `/graphql` endpoint.

