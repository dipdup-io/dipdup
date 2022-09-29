# Monitoring

In order to perform up-to-date and freshness checks DipDup provides a standard REST endpoint you can use together with Betteruptime or similar services that can search for a keyword in the response.

This check basically says that DipDup is not stuck and keeps receiving new data (last known block timestamp is not older than **three minutes** from now).  
Note that this is not enough to ensure everything works as expected, but it can at least cover the cases when there is an issue with the datasource or your indexer stops working due to an exception.  

### URI format

```
https://<your-indexer-host>/api/rest/dipdup_head_status?name=<datasource-uri>
```

If you have camel case enabled in the Hasura config:

```
https://<your-indexer-host>/api/rest/dipdupHeadStatus?name=<datasource-uri>
```

For example:
* [https://domains.dipdup.net/api/rest/dipdup_head_status?name=https://api.tzkt.io](https://domains.dipdup.net/api/rest/dipdup_head_status?name=https://api.tzkt.io)
* [https://juster.dipdup.net/api/rest/dipdupHeadStatus?name=https://api.tzkt.io](https://domains.dipdup.net/api/rest/dipdup_head_status?name=https://api.tzkt.io)

### Response

If the (latest block) head subscription state was updated less than **three minutes** ago, everything is **OK**:
```
{
  "dipdup_head_status": [
    {
      "status": "OK"
    }
  ]
}
```

Otherwise the state is considered **OUTDATED**:
```
{
  "dipdup_head_status": [
    {
      "status": "OUTDATED"
    }
  ]
}
```

### Custom checks

The default check looks like the following:

```sql
CREATE
OR REPLACE VIEW dipdup_head_status AS
SELECT
    name,
    CASE
        WHEN timestamp < NOW() - interval '3 minutes' THEN 'OUTDATED'
        ELSE 'OK'
    END AS status
FROM
    dipdup_head;
```

You can also create your custom alert endpoints using SQL views and functions and then converting them to Hasura REST endpoints.

> 💡 **SEE ALSO**
>
> * {{ #summary advanced/sql.md}}
> * {{ #summary graphql/rest.md}}