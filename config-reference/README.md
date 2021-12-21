# Config file reference

DipDup configuration is stored in YAML files of a specific format. By default, DipDup searches for `dipdup.yml` file in the current working directory, but you can provide any path with a `-c` CLI option:

```shell
dipdup -c configs/config.yml run
```

## General structure

DipDup configuration file consists of several logical blocks:

| | |
|-|-|
| Header               | `spec_version`* |
|                      | `package`* |
| Inventory            | `database`* |
|                      | `contracts`* |
|                      | `datasources`* |
| Index definitions    | `indexes` |
|                      | `templates` |
| Integrations         | `sentry`
|                      | `hasura` |
| Hooks                | `hooks` |
|                      | `jobs` |

`*`  — required sections

## Environment variables

DipDup supports compose-style variable expansion with optional default value:

```yaml
field: ${ENV_VAR:-default_value}
```

You can use environment variables throughout the configuration file, except for property names (YAML object keys).

## Merging config files

DipDup allows you to customize the configuration for a specific environment or a workflow. It works similar to docker-compose, but only for top-level sections. If you want to override a nested property, you need to recreate a whole top-level section. To merge several DipDup config files, provide `-c` command-line option multiple times:

```shell
dipdup -c dipdup.yml -c dipdup.prod.yml run
```

Run [`config export`](../cli-reference/config-export.md) command if unsure about final config used by DipDup.
