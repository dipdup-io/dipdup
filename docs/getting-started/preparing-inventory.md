# Preparing inventory

Developing a DipDup indexer begins with creating a YAML config file.

Before starting indexing, you need to set up several things:

* Contracts you want to process with your indexer. `operation` indexes will fetch sender/target/origination operations of this contract, `big_maps` ones it's big maps. See [12.2. contracts](../config/contracts.md) for details.
* Datasources used both by DipDup internally and user on demand. At least one of them must be a TzKT one. See [12.4. datasources](../config/datasources.md) for details.
* Indexes. See [12.7. indexes](../config/indexes/README.md) for details.

A minimal working example looks like this:

```yaml
{{ #include ../../src/demo_tzbtc/dipdup.yml }}
```
