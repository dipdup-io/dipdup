# Config file reference

## Naming

DipDup configuration file is usually stored on the top level of your project and has default name `dipdup.yml`. You can also have multiple configuration files and explicitly provide the target name via `-c` option when using CLI.

```text
dipdup -c custom-config.yml
```

## General structure

Configuration file consists of several logical blocks:

|  | Top level sections |
| :--- | :--- |
| Header | `spec_version` `package` |
| Inventory | `contracts` `datasources` |
| Indexer specifications | `indexes` `templates*` |
| Deployment options | `database` `sentry*` `hasura*` |
| Plugin settings | `mempool*` `metadata*` |

`*`  — optional sections

## Environment variables

DipDup supports compose-style variable expansion with optional default value:

```yaml
field: ${ENV_VAR:-default_value}
```

You can use environment variables throughout the configuration file except for the property names \(keys\).

## Multiple config files

DipDup allows you to customize configuration for a specific environment or a workflow. It works pretty much the same as in Docker Compose, but only for the top level sections \(i.e. you cannot override just a single nested property, you need to provide the entire new section\). In order to merge several DipDup files use `-c` command line option multiple times:

```text
dipdup -c dipdup.yml -c dipdup.prod.yml run
```

