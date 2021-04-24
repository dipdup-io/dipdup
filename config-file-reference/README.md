# Config file reference

## Naming

DipDup configuration file is usually stored on the top level of your project and has default name `dipdup.yml`. You can also have multiple configuration files and explicitly provide the target name via `-c` option when using CLI.

```text
dipdup -c custom-config.yml
```

## General structure

Сonfiguration file consists of several logical sections:

|  |  |
| :--- | :--- |
| Header | `spec_version` `package` |
| Inventory | `contracts` `datasources` |
| Indexer specifications | `indexes` `templates` |
| Deployment settings | `database` `hasura` |
| Plugin settings | `mempool` `metadata` |



## Environment variables



