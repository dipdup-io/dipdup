# sentry

Sentry is an error tracking software that can be used either as a service or on-premise. It dramatically improves the troubleshooting experience and requires nearly zero configuration. To start catching exceptions with Sentry in your project, add the following section in `dipdup.yml` config:

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

You can obtain Sentry DSN from the web interface at _Settings -> Projects -> <project\_name> -> Client Keys (DSN)_. The cool thing is that if you catch an exception and suspect there's a bug in DipDup, you can share this event with us using a public link (created at _Share_ menu).

> 🤓 **SEE ALSO**
> * [8.5. Sentry integration](../deployment/sentry.md)
