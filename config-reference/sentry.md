# sentry

Sentry is an error tracking software which can be used both in cloud and on-premise. It greatly improves troubleshooting experience and requires nearly zero configuration. To start catching exceptions with Sentry in your project add the following section in `dipdup.yml` config:

```yaml
sentry:
  dsn: https://...
  environment: dev
```

Sentry DSN can be obtained from the web interface at _Settings -&gt; Projects -&gt; project\_name -&gt; Client Keys \(DSN\)_. Cool thing is that if you catch an exception and suspect there's a bug in DipDup you can share this event with us using a public link \(created at _Share_ menu\).
