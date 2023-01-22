# sentry

```yaml
sentry:
  dsn: https://...
  environment: dev
  debug: False
```

| field | description |
| - | - |
| `dsn` | DSN of the Sentry instance |
| `environment` | Environment to report to Sentry (informational only) |
| `debug` | Catch warning messages and more context |

```admonish info title="See Also"
* {{ #summary deployment/sentry.md}}
```
