# Logging

To control the number of logs DipDup produces, set the `logging` field in config. It can be either a string or a mapping from logger names to logging levels.

```yaml
# Confugure dipdup and package loggers
logging: INFO

# Increase verbosity of some loggers
logging:
  dipdup.database: DEBUG
  aiosqlite: DEBUG

# Enable ALL logs
logging:
  '': DEBUG
```

By default only `dipdup` and `<package>` namespace loggers are affected. Here's a list of loggers we use internally you may consider enabling:

<!-- TODO: Gather logger names automatically to ensure they are up-to-date.  -->

| Logger Name       | Description                                               |
| ----------------- | --------------------------------------------------------- |
| dipdup            | Root logger                                               |
| dipdup.cli        | Messages related to DipDup's command-line interface (CLI) |
| dipdup.callback   |                                                           |
| dipdup.database   |                                                           |
| dipdup.http       |                                                           |
| dipdup.hasura     |                                                           |
| dipdup.project    |                                                           |
| dipdup.jobs       |                                                           |
| dipdup.datasource |                                                           |
| dipdup.yaml       |                                                           |
| dipdup.codegen    |                                                           |
| dipdup.config     |                                                           |
| dipdup.tzkt       |                                                           |
| dipdup.subsquid   |                                                           |
| dipdup.matcher    |                                                           |
| dipdup.fetcher    |                                                           |
| dipdup.model      |                                                           |
