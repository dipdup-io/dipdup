# Creating config

Developing a DipDup indexer begins with creating a YAML config file. You can find a minimal example to start indexing on the Quickstart page.

## General structure

DipDup configuration is stored in YAML files of a specific format. By default, DipDup searches for `dipdup.yml` file in the current working directory, but you can provide any path with a `-c` CLI option.

DipDup config file consists of several logical blocks:

{{ #include ../include/config-toc.md }}

**Header** contains two required fields, `package` and `spec_version`. They are used to identify the project and the version of the DipDup specification. All other fields in the config are optional.

**Inventory** specifies contracts that need to be indexed, datasources to fetch data from, and the database to store data in.

**Index definitions** define the index templates that will be used to index the contract data.

**Hook definitions** define callback functions that will be called manually or on schedule.

**Integrations** are used to integrate with third-party services.

**Tunables** affect the behavior of the whole framework.

## Merging config files

DipDup allows you to customize the configuration for a specific environment or workflow. It works similarly to docker-compose anchors but only for top-level sections. If you want to override a nested property, you need to recreate a whole top-level section. To merge several DipDup config files, provide the `-c` command-line option multiple times:

```shell
dipdup -c dipdup.yml -c dipdup.prod.yml run
```

Run `config export` command if unsure about the final config used by DipDup.

## Full example

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

Let's put it all together. The config below is an artificial example but contains almost all available options.

```yaml
{{ #include ../include/dipdup-full.yml }}
```
