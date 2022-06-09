# Command-line reference

If you have not installed DipDup yet refer to [4.1. Installation](../getting-started/installation.md) page.

## Specifying the path to config

By default, DipDup looks for a file named `dipdup.yml` in the current working directory. You can override that by explicitly specifying a path to config (one or many):

```shell
dipdup -c configs/dipdup.yml -c configs/dipdup.prod.yml COMMAND
```

See [Merging config files](../config#merging-config-files) for details.
