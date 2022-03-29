# Tuning datasources

All datasources now share the same code under the hood to communicate with underlying APIs via HTTP. Configs of all datasources and also Hasura's one can have an optional section `http` with any number of the following parameters set:

```yaml
datasources:
  tzkt:
    kind: tzkt
    ...
    http:
      cache: True
      retry_count: 10
      retry_sleep: 1
      retry_multiplier: 1.2
      ratelimit_rate: 100
      ratelimit_period: 60
      connection_limit: 25
      batch_size: 10000
hasura:
  url: http://hasura:8080
  http:
    ...
```

| field | description |
| - | - |
| `cache` | Whether to cache responses |
| `retry_count` | Number of retries after request failed before giving up |
| `retry_sleep` | Sleep time between retries |
| `retry_multiplier` | Multiplier for sleep time between retries |
| `ratelimit_rate` | Number of requests per period ("drops" in leaky bucket) |
| `ratelimit_period` | Period for rate limiting in seconds |
| `connection_limit` | Number of simultaneous connections |
| `connection_timeout` | Connection timeout in seconds |
| `batch_size` | Number of items fetched in a single paginated request (for some APIs) |

Each datasource has its defaults. Usually, there's no reason to alter these settings unless you use self-hosted instances of TzKT or  other datasource.

By default, DipDup retries failed requests infinitely, exponentially increasing the delay between attempts. Set `retry_count` parameter to limit the number of attempts.

`batch_size` parameter is TzKT-specific. By default, DipDup limit requests to 10000 items, the maximum value allowed on public instances provided by Baking Bad. Decreasing this value will reduce the time required for TzKT to process a single request and thus reduce the load. You can achieve the same effect (but limited to synchronizing multiple indexes concurrently) by reducing `connection_limit` parameter.


> 🤓 **SEE ALSO**
>
> * [Tortoise ORM documentation](https://tortoise-orm.readthedocs.io/en/latest/)
> * [Tortoise ORM examples](https://tortoise-orm.readthedocs.io/en/latest/examples.html)
> * [8.1. Database engines](../deployment/database-engines.md)
> * [8.9. Backup and restore](../deployment/backups.md)


See [12.4. datasources](../../config-reference/datasources.md) for details.
