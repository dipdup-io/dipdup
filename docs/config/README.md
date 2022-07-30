# Config file reference

DipDup configuration is stored in YAML files of a specific format. By default, DipDup searches for `dipdup.yml` file in the current working directory, but you can provide any path with a `-c` CLI option:

```shell
dipdup -c configs/config.yml run
```

## General structure

DipDup configuration file consists of several logical blocks:

| | | |
|-|-|-|
| Header               | `spec_version`* | {{ #summary config/spec_version.md}} |
|                      | `package`*      | {{ #summary config/package.md}} |
| Inventory            | `database`      | {{ #summary config/database.md}} |
|                      | `contracts`     | {{ #summary config/contracts.md}} |
|                      | `datasources`   | {{ #summary config/datasources.md}} |
| Index definitions    | `indexes`       | {{ #summary config/indexes/README.md}} |
|                      | `templates`     | {{ #summary config/templates.md}} |
| Hook definitions     | `hooks`         | {{ #summary config/hooks.md}} |
|                      | `jobs`          | {{ #summary config/jobs.md}} |
| Integrations         | `sentry`        | {{ #summary config/sentry.md}} |
|                      | `hasura`        | {{ #summary config/hasura.md}} |
|                      | `prometheus`    | {{ #summary config/prometheus.md}} |
| Tunables             | `advanced`      | {{ #summary config/advanced.md}} |
|                      | `logging`       | {{ #summary config/logging.md}} |

`*` — required fields

## Merging config files

DipDup allows you to customize the configuration for a specific environment or a workflow. It works similar to docker-compose, but only for top-level sections. If you want to override a nested property, you need to recreate a whole top-level section. To merge several DipDup config files, provide the `-c` command-line option multiple times:

```shell
dipdup -c dipdup.yml -c dipdup.prod.yml run
```

Run [`config export`](../cli-reference.md#dipdup-config-export) command if unsure about the final config used by DipDup.
