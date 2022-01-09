# Changelog

Please use [this](https://docs.gitlab.com/ee/development/changelog.html) document as guidelines to keep a changelog.

## 4.0.3 - 2022-01-09

### Fixed

* tzkt: Fixed parsing parameter with an optional value.

## 4.0.2 - 2022-01-06

### Added

* tzkt: Added optional `delegate_address` and `delegate_alias` fields to `OperationData`.

### Fixed

* tzkt: Fixed crash due to unprocessed pysignalr exception.
* tzkt: Fixed parsing `OperationData.amount` field.
* tzkt: Fixed parsing storage with top-level boolean fields.

## 4.0.1 - 2021-12-30

### Fixed

* codegen: Fixed generating storage typeclasses with `Union` fields.
* codegen: Fixed preprocessing contract JSONSchema.
* index: Fixed processing reindexing reason saved in the database.
* tzkt: Fixed processing operations with default entrypoint and empty parameter.
* tzkt: Fixed crash while recursively applying bigmap diffs to the storage.

### Performance

* tzkt: Increased speed of applying bigmap diffs to operation storage.

## 4.0.0 - 2021-12-24

This release contains no changes except for the version number.

## 4.0.0-rc3 - 2021-12-20

### Fixed

* cli: Fixed missing `schema approve --hashes` argument.
* codegen: Fixed contract address used instead of an alias when typename is not set.
* tzkt: Fixed processing operations with entrypoint `default`.
* tzkt: Fixed regression in processing migration originations.
* tzkt: Fixed filtering of big map diffs by the path.

### Removed

* cli: Removed deprecated `run --oneshot` argument and `clear-cache` command.

## 4.0.0-rc2 - 2021-12-11

### ⚠ Migration

* Run `dipdup init` command to generate `on_synchronized` hook stubs.

### Added

* hooks: Added `on_synchronized` hook, which fires each time all indexes reach realtime state.

### Fixed

* cli: Fixed config not being verified when invoking some commands.
* codegen: Fixed generating callback arguments for untyped operations.
* index: Fixed incorrect log messages, remove duplicate ones.
* index: Fixed crash while processing storage of some contracts.
* index: Fixed matching of untyped operations filtered by `source` field ([@pravin-d](https://github.com/pravin-d)).

### Performance

* index: Checks performed on each iteration of the main DipDup loop are slightly faster now.

## 4.0.0-rc1 - 2021-12-02

### ⚠ Migration

* Run `dipdup schema approve` command on every database you want to use with 4.0.0-rc1. Running `dipdup migrate` is not necessary since `spec_version` hasn't changed in this release.

### Added

* cli: Added `run --early-realtime` flag to establish a realtime connection before all indexes are synchronized.
* cli: Added `run --merge-subscriptions` flag to subscribe to all operations/big map diffs during realtime indexing.
* cli: Added `status` command to print the current status of indexes from the database.
* cli: Added `config export [--unsafe]` command to print config after resolving all links and variables.
* cli: Added `cache show` command to get information about file caches used by DipDup.
* config: Added `first_level` and `last_level` optional fields to `TemplateIndexConfig`. These limits are applied after ones from the template itself.
* config: Added `daemon` boolean field to `JobConfig` to run a single callback indefinitely. Conflicts with `crontab` and `interval` fields.
* config: Added `advanced` top-level section.

### Fixed

* cli: Fixed crashes and output inconsistency when piping DipDup commands.
* cli: Fixed `schema wipe --immune` flag being ignored.
* codegen: Fixed missing imports in handlers generated during init.
* coinbase: Fixed possible data inconsistency caused by caching enabled for method `get_candles`.
* http: Fixed increasing sleep time between failed request attempts.
* index: Fixed invocation of head index callback.
* index: Fixed `CallbackError` raised instead of `ReindexingRequiredError` in some cases.
* tzkt: Fixed resubscribing when realtime connectivity is lost for a long time.
* tzkt: Fixed sending useless subscription requests when adding indexes in runtime.
* tzkt: Fixed `get_originated_contracts` and `get_similar_contracts` methods whose output was limited to `HTTPConfig.batch_size` field.
* tzkt: Fixed lots of SignalR bugs by replacing `aiosignalrcore` library with `pysignalr`.

## Changed

* cli: `dipdup schema wipe` command now requires confirmation when invoked in the interactive shell.
* cli: `dipdup schema approve` command now also causes a recalculation of schema and index config hashes.
* index: DipDup will recalculate respective hashes if reindexing is triggered with `config_modified: ignore` or `schema_modified: ignore` in advanced config.

### Deprecated

* cli: `run --oneshot` option is deprecated and will be removed in the next major release. The oneshot mode applies automatically when `last_level` field is set in the index config.
* cli: `clear-cache` command is deprecated and will be removed in the next major release. Use `cache clear` command instead.

### Performance

* config: Configuration files are loaded 10x times faster.
* index: Number of operations processed by matcher reduced by 40%-95% depending on the number of addresses and entrypoints used.
* tzkt: Rate limit was increased. Try to set `connection_timeout` to a higher value if requests fail with `ConnectionTimeout` exception.
* tzkt: Improved performance of response deserialization. 

## 3.1.3 - 2021-11-15

### Fixed

* codegen: Fixed missing imports in operation handlers. 
* codegen: Fixed invalid imports and arguments in big_map handlers.

## 3.1.2 - 2021-11-02

### Fixed

* Fixed crash occurred during synchronization of big map indexes.

## 3.1.1 - 2021-10-18

### Fixed

* Fixed loss of realtime subscriptions occurred after TzKT API outage.
* Fixed updating schema hash in `schema approve` command.
* Fixed possible crash occurred while Hasura is not ready.

## 3.1.0 - 2021-10-12

### Added

* New index class `HeadIndex` (configuration: [`dipdup.config.HeadIndexConfig`](https://github.com/dipdup-net/dipdup-py/blob/master/src/dipdup/config.py#L778)). Use this index type to handle head (limited block header content) updates. This index type is realtime-only: historical data won't be indexed during the synchronization stage.
* Added three new commands: `schema approve`, `schema wipe`, and `schema export`. Run `dipdup schema --help` command for details.

### Changed

* Triggering reindexing won't lead to dropping the database automatically anymore. `ReindexingRequiredError` is raised instead. `--forbid-reindexing` option has become default.
* `--reindex` option is removed. Use `dipdup schema wipe` instead.
* Values of `dipdup_schema.reindex` field updated to simplify querying database. See [`dipdup.enums.ReindexingReason`](https://github.com/dipdup-net/dipdup-py/blob/master/src/dipdup/enums.py) class for possible values.

### Fixed

* Fixed `ReindexRequiredError` not being raised when running DipDup after reindexing was triggered.
* Fixed index config hash calculation. Hashes of existing indexes in a database will be updated during the first run.
* Fixed issue in `BigMapIndex` causing the partial loss of big map diffs.
* Fixed printing help for CLI commands.
* Fixed merging storage which contains specific nested structures.

### Improved

* Raise `DatabaseConfigurationError` exception when project models are not compatible with GraphQL.
* Another bunch of performance optimizations. Reduced DB pressure, speeded up parallel processing lots of indexes.
* Added initial set of performance benchmarks (run: `./scripts/run_benchmarks.sh`)

## 3.0.4 - 2021-10-04

### Improved

* A significant increase in indexing speed.

### Fixed

* Fixed unexpected reindexing caused by the bug in processing zero- and single-level rollbacks.
* Removed unnecessary file IO calls that could cause `PermissionError` exception in Docker environments.
* Fixed possible violation of block-level atomicity during realtime indexing.

### Changes

* Public methods of `TzktDatasource` now return immutable sequences.

## 3.0.3 - 2021-10-01

### Fixed

* Fixed processing of single-level rollbacks emitted before rolled back head.

## 3.0.2 - 2021-09-30

### Added

* Human-readable `CHANGELOG.md` 🕺
* Two new options added to `dipdup run` command:
  * `--forbid-reindexing` – raise `ReindexingRequiredError` instead of truncating database when reindexing is triggered for any reason. To continue indexing with existing database run `UPDATE dipdup_schema SET reindex = NULL;`
  * `--postpone-jobs` – job scheduler won't start until all indexes are synchronized. 

### Changed

* Migration to this version requires reindexing.
* `dipdup_index.head_id` foreign key removed. `dipdup_head` table still contains the latest blocks from Websocket received by each datasource.

### Fixed

* Removed unnecessary calls to TzKT API.
* Fixed removal of PostgreSQL extensions (`timescaledb`, `pgcrypto`) by function `truncate_database` triggered on reindex.
* Fixed creation of missing project package on `init`.
* Fixed invalid handler callbacks generated on `init`.
* Fixed detection of existing types in the project.
* Fixed race condition caused by event emitter concurrency.
* Capture unknown exceptions with Sentry before wrapping to `DipDupError`.
* Fixed job scheduler start delay.
* Fixed processing of reorg messages.

## 3.0.1 - 2021-09-24

### Added

* Added `get_quote` and `get_quotes` methods to `TzKTDatasource`.

### Fixed

* Defer spawning index datasources until initial sync is complete. It helps to mitigate some WebSocket-related crashes, but initial sync is a bit slower now.
* Fixed possible race conditions in `TzKTDatasource`.
* Start `jobs` scheduler after all indexes sync with a current head to speed up indexing.
