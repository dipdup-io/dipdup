# Changelog

## 3.1.3 - 2021-11-15

### Fixed

* codegen: Fixed missing imports in operation handlers. 
* codegen: Fixed invalid imports and arguments in big_map handlers.

## 3.1.2 - 2021-11-02

### Fixed

* Fixed crash occurred during synchronization of big map indexes.

## 3.1.1 - 2021-10-18

### Fixed

* Fixed loss of real-time subscriptions occurred after TzKT API outage.
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
* Fixed possible violation of block-level atomicity during real-time indexing.

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
