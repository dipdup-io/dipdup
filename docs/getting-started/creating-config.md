# Creating config

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

Developing a DipDup indexer begins with creating a YAML config file. You can find a minimal example to start indexing on the Quckstart page. This page will cover all available options and when they are useful. When you decide what config sections you need in your project, follow {{ #summary config/README.md }} for detailed instructions.

<!-- Header	spec_version*	14.14. spec_version
	package*	14.11. package
Inventory	database	14.4. database
	contracts	14.3. contracts
	datasources	14.5. datasources
Index definitions	indexes	14.8. indexes
	templates	14.15. templates
Hook definitions	hooks	14.7. hooks
	jobs	14.9. jobs
Integrations	sentry	14.13. sentry
	hasura	14.6. hasura
	prometheus	14.12. prometheus
Tunables	advanced	14.2. advanced
	logging	14.10. logging

* Contracts you want to process with your indexer. `operation` indexes will fetch sender/target/origination operations of this contract, `big_maps` ones its big maps. See [12.2. contracts](../config/contracts.md) for details.
* Datasources used both by DipDup internally and user on demand.
* Indexes. -->

Let's put it all together. Config below is an artificial example but contains almost all available options.

```yaml
{{ #include _dipdup-full.yml }}
```
