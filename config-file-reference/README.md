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
| Deployment options | `database` `hasura*` |
| Plugin settings | `mempool*` `metadata*` |

`*`  — optional sections

## Environment variables

DipDup supports compose-style variable expansion with optional default value:

```yaml
field: ${ENV_VAR:-default_value}
```

You can use environment variables throughout the configuration file except for the property names \(keys\).

