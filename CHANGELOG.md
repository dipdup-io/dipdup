# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], and this project adheres to [Semantic Versioning].

## [Unreleased]

### Fixed

- cli: Configure package logger in addition to `dipdup` one.
- tzkt: Fixed deserializing `EventData` model.

## [6.2.0] - 2022-10-12

### Added

- cli: `new` command to create a new project interactively.
- cli: `install/update/uninstall` commands to manage local DipDup installation.
- index: New index kind `event` to process contract events.
- install: New interactive installer based on pipx (`install.py` or `dipdup-install`).

### Fixed

- cli: Fixed commands that don't require a valid config yet crash with `ConfigurationError`.
- codegen: Fail on demand when `datamodel-codegen` is not available.
- codegen: Fixed Jinja2 template caching.
- config: Allow `sentry.dsn` field to be empty.
- config: Fixed greedy environment variable regex.
- hooks: Raise a `FeatureAvailabilityHook` instead of a warning when trying to execute hooks on SQLite.

### Improved

- cli: Detect `src/` layout when guessing package path.
- codegen: Improved cross-platform compatibility.
- config: `sentry.user_id` option to set user ID for Sentry (affects release adoption data).
- sentry: Detect environment when not set in config (docker/gha/tests/local)
- sentry: Expose more tags under the `dipdup` namespace.

### Performance

- cli: Up to 5x faster startup for some commands.

### Security

- sentry: Prevent Sentry from leaking hostname if `server_name` is not set.
- sentry: Notify about using Sentry when DSN is set or crash reporting is enabled.

### Other

- ci: A significantly faster execution of GitHub Actions.
- docs: Updated "Contributing Guide" page.

## [6.1.3] - 2022-09-21

### Added

- sentry: Enable crash-free session reporting.

### Fixed

- metadata: Updated protocol aliases.
- sentry: Unwrap `CallbackError` traceback to fix event grouping.
- sentry: Hide "attempting to send..." message on shutdown.

### Other

- ci: Do not build default and `-pytezos` nightly images.

## [6.1.2] - 2022-09-16

### Added

- config: Added `alias` field to operation pattern items.
- tzkt: Added quote field `gbp`.

### Fixed

- config: Require aliases for multiple operations with the same entrypoint.
- http: Raise `InvalidRequestError` on 204 No Content responses.
- tzkt: Verify API version on datasource initialization.
- tzkt: Remove deprecated block field `priority`.

## [6.1.1] - 2022-09-01

### Fixed

- ci: Lock Pydantic to 1.9.2 to avoid breaking changes in dataclasses.

## [6.1.0] - 2022-08-30

### Added

- ci: Build `arm64` images for M1/M2 silicon.
- ci: Build `-slim` images based on Alpine Linux.
- ci: Introduced official MacOS support.
- ci: Introduced interactive installer (dipdup.io/install.py).

## [6.0.1] - 2022-08-19

### Fixed

- codegen: Fixed invalid `models.py` template.
- context: Do not wrap known exceptions with `CallbackError`.
- database: Raise `DatabaseConfigurationError` when backward relation name equals table name.
- database: Wrap schema wiping in a transaction to avoid orphaned tables in the immune schema.
- hasura: Fixed processing M2M relations.
- sentry: Fixed "invalid value `environment`" error.
- sentry: Ignore events from project callbacks when `crash_reporting` is enabled.

## [6.0.0] - 2022-08-08

This release contains no changes except for the version number.

## [6.0.0rc2] - 2022-08-06

### Added

- config: Added `advanced.crash_reporting` flag to enable reporting crashes to Baking Bad.
- dipdup: Save Sentry crashdump in `/tmp/dipdup/crashdumps/XXXXXXX.json` on a crash.

### Fixed

- config: Do not perform env variable substitution in commented-out lines.

### Removed

- cli: `--logging-config` option is removed.
- cli: All `run` command flags are removed. Use the `advanced` section of the config.
- cli: `cache show` and `cache clear` commands are removed.
- config: `http.cache` flag is removed.

## [6.0.0-rc1] - 2022-07-26

### Added

- cli: Added `config export --full` flag to resolve templates before printing config.
- config: Added `advanced.rollback_depth` field, a number of levels to keep in a database for rollback.
- context: Added `rollback` method to perform database rollback.
- database: Added an internal `ModelUpdate` model to store the latest database changes.

### Fixed

- prometheus: Fixed updating `dipdup_index_handlers_matched_total` metric.

### Changed

- codegen: `on_index_rollback` hook calls `ctx.rollback` by default.
- database: Project models must be subclassed from `dipdup.models.Model`
- database: `bulk_create` and `bulk_update` model methods are no longer supported.

### Removed

- hooks: Removed deprecated `on_rollback` hook.
- index: Do not try to avoid single-level rollbacks by comparing operation hashes.

## [5.2.5] - 2022-07-26

### Fixed

- index: Fixed crash when adding an index with new subscriptions in runtime.

## [5.2.4] - 2022-07-17

### Fixed

- cli: Fixed logs being printed to stderr instead of stdout.
- config: Fixed job scheduler not starting when config contains no indexes.

## [5.2.3] - 2022-07-07

### Added

- sentry: Allow customizing `server_name` and `release` tags with corresponding fields in Sentry config.

### Fixed

- cli: Fixed `hasura configure` command crash when models have empty `Meta.table`.
- config: Removed secrets from config `__repr__`.

## [5.2.2] - 2022-07-03

### Fixed

- hasura: Fixed metadata generation.

## [5.2.1] - 2022-07-02

### Fixed

- cli: Fixed setting default logging level.
- hasura: Fixed metadata generation for relations with a custom field name.
- hasura: Fixed configuring existing instances after changing `camel_case` field in config.

## [5.2.0] - 2022-06-28

### Added

- config: Added `logging` config field.
- config: Added `hasura.create_source` flag to create PostgreSQL source if missing.

### Fixed

- hasura: Do not apply table customizations to tables from other sources.

### Deprecated

- cli: `--logging-config` option is deprecated.
- cli: All `run` command flags are deprecated. Use the `advanced` section of the config.
- cli: `cache show` and `cache clear` commands are deprecated.
- config: `http.cache` flag is deprecated.

## [5.1.7] - 2022-06-15

### Fixed

- index: Fixed `token_transfer` index not receiving realtime updates.

## [5.1.6] - 2022-06-08

### Fixed

- cli: Commands with `--help` option no longer require a working DipDup config.
- index: Fixed crash with `RuntimeError` after continuous realtime connection loss.

### Performance

- cli: Lazy import dependencies to speed up startup.

### Other

- docs: Migrate docs from GitBook to mdbook.

## [5.1.5] - 2022-06-05

### Fixed

- config: Fixed crash when rollback hook is about to be called.

## [5.1.4] - 2022-06-02

### Fixed

- config: Fixed `OperationIndexConfig.types` field being partially ignored.
- index: Allow mixing oneshot and regular indexes in a single config.
- index: Call rollback hook instead of triggering reindex when single-level rollback has failed.
- index: Fixed crash with `RuntimeError` after continuous realtime connection loss.
- tzkt: Fixed `origination` subscription missing when `merge_subscriptions` flag is set.

### Performance

- ci: Decrease the size of generic and `-pytezos` Docker images by 11% and 16%, respectively.

## [5.1.3] - 2022-05-26

### Fixed

- database: Fixed special characters in password not being URL encoded.

### Performance

- context: Do not reinitialize config when adding a single index.

## [5.1.2] - 2022-05-24

### Added

- tzkt: Added `originated_contract_tzips` field to `OperationData`.

### Fixed

- jobs: Fixed jobs with `daemon` schedule never start.
- jobs: Fixed failed jobs not throwing exceptions into the main loop.

### Other

- database: Tortoise ORM updated to `0.19.1`.

## [5.1.1] - 2022-05-13

### Fixed

- index: Ignore indexes with different message types on rollback.
- metadata: Add `ithacanet` to available networks.

## [5.1.0] - 2022-05-12

### Added

- ci: Push `X` and `X.Y` tags to the Docker Hub on release.
- cli: Added `config env` command to export env-file with default values.
- cli: Show warning when running an outdated version of DipDup.
- hooks: Added a new hook `on_index_rollback` to perform per-index rollbacks.

### Fixed

- index: Fixed fetching `migration` operations.
- tzkt: Fixed possible data corruption when using the `buffer_size` option.
- tzkt: Fixed reconnection due to `websockets` message size limit.

### Deprecated

- hooks: The `on_rollback` default hook is superseded by `on_index_rollback` and will be removed later.

## [5.0.4] - 2022-05-05

### Fixed

- exceptions: Fixed incorrect formatting and broken links in help messages.
- index: Fixed crash when the only index in config is `head`.
- index: Fixed fetching originations during the initial sync.

## [5.0.3] - 2022-05-04

### Fixed

- index: Fixed crash when no block with the same level arrived after a single-level rollback.
- index: Fixed setting initial index level when `IndexConfig.first_level` is set.
- tzkt: Fixed delayed emitting of buffered realtime messages.
- tzkt: Fixed inconsistent behavior of `first_level`/`last_level` arguments in different getter methods.

## [5.0.2] - 2022-04-21

### Fixed

- context: Fixed reporting incorrect reindexing reason.
- exceptions: Fixed crash with `FrozenInstanceError` when an exception is raised from a callback.
- jobs: Fixed graceful shutdown of daemon jobs.

### Improved

- codegen: Refined `on_rollback` hook template.
- exceptions: Updated help messages for known exceptions.
- tzkt: Do not request reindexing if missing subgroups have matched no handlers.

## [5.0.1] - 2022-04-12

### Fixed

- cli: Fixed `schema init` command crash with SQLite databases.
- index: Fixed spawning datasources in oneshot mode.
- tzkt: Fixed processing realtime messages.

## [5.0.0] - 2022-04-08

This release contains no changes except for the version number.

## [5.0.0-rc4] - 2022-04-04

### Added

- tzkt: Added ability to process realtime messages with lag.

## [4.2.7] - 2022-04-02

### Fixed

- config: Fixed `jobs` config section validation.
- hasura: Fixed metadata generation for v2.3.0 and above.
- tzkt: Fixed `get_originated_contracts` and `get_similar_contracts` methods response.

## [5.0.0-rc3] - 2022-03-28

### Added

- config: Added `custom` section to store arbitrary user data.

### Fixed

- config: Fixed default SQLite path (`:memory:`).
- tzkt: Fixed pagination in several getter methods.
- tzkt: Fixed data loss when `skip_history` option is enabled.

### Removed

- config: Removed dummy `advanced.oneshot` flag.
- cli: Removed `docker init` command.
- cli: Removed dummy `schema approve --hashes` flag.

## [5.0.0-rc2] - 2022-03-13

### Fixed

- tzkt: Fixed crash in methods that do not support cursor pagination.
- prometheus: Fixed invalid metric labels. 

## [5.0.0-rc1] - 2022-03-02

### Added

- metadata: Added `metadata_interface` feature flag to expose metadata in TzKT format.
- prometheus: Added ability to expose Prometheus metrics.
- tzkt: Added missing fields to the `HeadBlockData` model.
- tzkt: Added `iter_...` methods to iterate over item batches.

### Fixed

- tzkt: Fixed possible OOM while calling methods that support pagination.
- tzkt: Fixed possible data loss in `get_originations` and `get_quotes` methods.

### Changed

- tzkt: Added `offset` and `limit` arguments to all methods that support pagination.

### Removed

- bcd: Removed `bcd` datasource and config section.

### Performance

- dipdup: Use fast `orjson` library instead of built-in `json` where possible.

## [4.2.6] - 2022-02-25

### Fixed

- database: Fixed generating table names from uppercase model names.
- http: Fixed bug that leads to caching invalid responses on the disk.
- tzkt: Fixed processing realtime messages with data from multiple levels.

## [4.2.5] - 2022-02-21

### Fixed

- database: Do not add the `schema` argument to the PostgreSQL connection string when not needed.
- hasura: Wait for Hasura to be configured before starting indexing.

## [4.2.4] - 2022-02-14

### Added

- config: Added `http` datasource to making arbitrary http requests.

### Fixed

- context: Fixed crash when calling `fire_hook` method.
- context: Fixed `HookConfig.atomic` flag, which was ignored in `fire_hook` method.
- database: Create missing tables even if `Schema` model is present.
- database: Fixed excess increasing of `decimal` context precision.
- index: Fixed loading handler callbacks from nested packages ([@veqtor](https://github.com/veqtor)).

### Other

- ci: Added GitHub Action to build and publish Docker images for each PR opened.

## [4.2.3] - 2022-02-08

### Fixed

- ci: Removed `black 21.12b0` dependency since bug in `datamodel-codegen-generator` is fixed.
- cli: Fixed `config export` command crash when `advanced.reindex` dictionary is present.
- cli: Removed optionals from `config export` output so the result can be loaded again.
- config: Verify `advanced.scheduler` config for the correctness and unsupported features.
- context: Fixed ignored `wait` argument of `fire_hook` method.
- hasura: Fixed processing relation fields with missing `related_name`.
- jobs: Fixed default `apscheduler` config.
- tzkt: Fixed crash occurring when reorg message is the first one received by the datasource.

## [4.2.2] - 2022-02-01

### Fixed

- config: Fixed `ipfs` datasource config.

## [4.2.1] - 2022-01-31

### Fixed

- ci: Added `black 21.12b0` dependency to avoid possible conflict with `datamodel-codegen-generator`.

## [4.2.0] - 2022-01-31

### Added

- context: Added `wait` argument to `fire_hook` method to escape current transaction context.
- context: Added `ctx.get_<kind>_datasource` helpers to avoid type casting.
- hooks: Added ability to configure `apscheduler` with `AdvancedConfig.scheduler` field.
- http: Added `request` method to send arbitrary requests (affects all datasources).
- ipfs: Added `ipfs` datasource to download JSON and binary data from IPFS.

### Fixed

- http: Removed dangerous method `close_session`.
- context: Fixed help message of `IndexAlreadyExistsError` exception.

### Deprecated

- bcd: Added deprecation notice.

### Other

- dipdup: Removed unused internal methods.

## [4.1.2] - 2022-01-27

### Added

- cli: Added `schema wipe --force` argument to skip confirmation prompt.

### Fixed

- cli: Show warning about deprecated `--hashes` argument
- cli: Ignore `SIGINT` signal when shutdown is in progress.
- sentry: Ignore exceptions when shutdown is in progress.

## [4.1.1] - 2022-01-25

### Fixed

- cli: Fixed stacktraces missing on exception.
- cli: Fixed wrapping `OSError` with `ConfigurationError` during config loading.
- hasura: Fixed printing help messages on `HasuraError`.
- hasura: Preserve a list of sources in Hasura Cloud environments.
- hasura: Fixed `HasuraConfig.source` config option.

### Changed

- cli: Unknown exceptions are no longer wrapped with `DipDupError`.

### Performance

- hasura: Removed some useless requests.

## [4.1.0] - 2022-01-24

### Added

- cli: Added `schema init` command to initialize database schema.
- cli: Added `--force` flag to `hasura configure` command.
- codegen: Added support for subpackages inside callback directories.
- hasura: Added `dipdup_head_status` view and REST endpoint.
- index: Added an ability to skip historical data while synchronizing `big_map` indexes.
- metadata: Added `metadata` datasource.
- tzkt: Added `get_big_map` and `get_contract_big_maps` datasource methods.

## [4.0.5] - 2022-01-20

### Fixed

- index: Fixed deserializing manually modified typeclasses.

## [4.0.4] - 2022-01-17

### Added

- cli: Added `--keep-schemas` flag to `init` command to preserve JSONSchemas along with generated types.

### Fixed

- demos: Tezos Domains and Homebase DAO demos were updated from edo2net to mainnet contracts.
- hasura: Fixed missing relations for models with `ManyToManyField` fields.
- tzkt: Fixed parsing storage with nested structures.

### Performance

- dipdup: Minor overall performance improvements.

### Other

- ci: Cache virtual environment in GitHub Actions.
- ci: Detect CI environment and skip tests that fail in GitHub Actions.
- ci: Execute tests in parallel with `pytest-xdist` when possible.
- ci: More strict linting rules of `flake8`.

## [4.0.3] - 2022-01-09

### Fixed

- tzkt: Fixed parsing parameter with an optional value.

## [4.0.2] - 2022-01-06

### Added

- tzkt: Added optional `delegate_address` and `delegate_alias` fields to `OperationData`.

### Fixed

- tzkt: Fixed crash due to unprocessed pysignalr exception.
- tzkt: Fixed parsing `OperationData.amount` field.
- tzkt: Fixed parsing storage with top-level boolean fields.

## [4.0.1] - 2021-12-30

### Fixed

- codegen: Fixed generating storage typeclasses with `Union` fields.
- codegen: Fixed preprocessing contract JSONSchema.
- index: Fixed processing reindexing reason saved in the database.
- tzkt: Fixed processing operations with default entrypoint and empty parameter.
- tzkt: Fixed crash while recursively applying bigmap diffs to the storage.

### Performance

- tzkt: Increased speed of applying bigmap diffs to operation storage.

## [4.0.0] - 2021-12-24

This release contains no changes except for the version number.

## [4.0.0-rc3] - 2021-12-20

### Fixed

- cli: Fixed missing `schema approve --hashes` argument.
- codegen: Fixed contract address used instead of an alias when typename is not set.
- tzkt: Fixed processing operations with entrypoint `default`.
- tzkt: Fixed regression in processing migration originations.
- tzkt: Fixed filtering of big map diffs by the path.

### Removed

- cli: Removed deprecated `run --oneshot` argument and `clear-cache` command.

## [4.0.0-rc2] - 2021-12-11

### Migration

- Run `dipdup init` command to generate `on_synchronized` hook stubs.

### Added

- hooks: Added `on_synchronized` hook, which fires each time all indexes reach realtime state.

### Fixed

- cli: Fixed config not being verified when invoking some commands.
- codegen: Fixed generating callback arguments for untyped operations.
- index: Fixed incorrect log messages, remove duplicate ones.
- index: Fixed crash while processing storage of some contracts.
- index: Fixed matching of untyped operations filtered by `source` field ([@pravin-d](https://github.com/pravin-d)).

### Performance

- index: Checks performed on each iteration of the main DipDup loop are slightly faster now.

## [4.0.0-rc1] - 2021-12-02

### Migration

- Run `dipdup schema approve` command on every database you want to use with 4.0.0-rc1. Running `dipdup migrate` is not necessary since `spec_version` hasn't changed in this release.

### Added

- cli: Added `run --early-realtime` flag to establish a realtime connection before all indexes are synchronized.
- cli: Added `run --merge-subscriptions` flag to subscribe to all operations/big map diffs during realtime indexing.
- cli: Added `status` command to print the current status of indexes from the database.
- cli: Added `config export [--unsafe]` command to print config after resolving all links and variables.
- cli: Added `cache show` command to get information about file caches used by DipDup.
- config: Added `first_level` and `last_level` optional fields to `TemplateIndexConfig`. These limits are applied after ones from the template itself.
- config: Added `daemon` boolean field to `JobConfig` to run a single callback indefinitely. Conflicts with `crontab` and `interval` fields.
- config: Added `advanced` top-level section.

### Fixed

- cli: Fixed crashes and output inconsistency when piping DipDup commands.
- cli: Fixed `schema wipe --immune` flag being ignored.
- codegen: Fixed missing imports in handlers generated during init.
- coinbase: Fixed possible data inconsistency caused by caching enabled for method `get_candles`.
- http: Fixed increasing sleep time between failed request attempts.
- index: Fixed invocation of head index callback.
- index: Fixed `CallbackError` raised instead of `ReindexingRequiredError` in some cases.
- tzkt: Fixed resubscribing when realtime connectivity is lost for a long time.
- tzkt: Fixed sending useless subscription requests when adding indexes in runtime.
- tzkt: Fixed `get_originated_contracts` and `get_similar_contracts` methods whose output was limited to `HTTPConfig.batch_size` field.
- tzkt: Fixed lots of SignalR bugs by replacing `aiosignalrcore` library with `pysignalr`.

## Changed

- cli: `dipdup schema wipe` command now requires confirmation when invoked in the interactive shell.
- cli: `dipdup schema approve` command now also causes a recalculation of schema and index config hashes.
- index: DipDup will recalculate respective hashes if reindexing is triggered with `config_modified: ignore` or `schema_modified: ignore` in advanced config.

### Deprecated

- cli: `run --oneshot` option is deprecated and will be removed in the next major release. The oneshot mode applies automatically when `last_level` field is set in the index config.
- cli: `clear-cache` command is deprecated and will be removed in the next major release. Use `cache clear` command instead.

### Performance

- config: Configuration files are loaded 10x times faster.
- index: Number of operations processed by matcher reduced by 40%-95% depending on the number of addresses and entrypoints used.
- tzkt: Rate limit was increased. Try to set `connection_timeout` to a higher value if requests fail with `ConnectionTimeout` exception.
- tzkt: Improved performance of response deserialization. 

## [3.1.3] - 2021-11-15

### Fixed

- codegen: Fixed missing imports in operation handlers. 
- codegen: Fixed invalid imports and arguments in big_map handlers.

## [3.1.2] - 2021-11-02

### Fixed

- Fixed crash occurred during synchronization of big map indexes.

## [3.1.1] - 2021-10-18

### Fixed

- Fixed loss of realtime subscriptions occurred after TzKT API outage.
- Fixed updating schema hash in `schema approve` command.
- Fixed possible crash occurred while Hasura is not ready.

## [3.1.0] - 2021-10-12

### Added

- New index class `HeadIndex` (configuration: [`dipdup.config.HeadIndexConfig`](https://github.com/dipdup-net/dipdup/blob/master/src/dipdup/config.py#L778)). Use this index type to handle head (limited block header content) updates. This index type is realtime-only: historical data won't be indexed during the synchronization stage.
- Added three new commands: `schema approve`, `schema wipe`, and `schema export`. Run `dipdup schema --help` command for details.

### Changed

- Triggering reindexing won't lead to dropping the database automatically anymore. `ReindexingRequiredError` is raised instead. `--forbid-reindexing` option has become default.
- `--reindex` option is removed. Use `dipdup schema wipe` instead.
- Values of `dipdup_schema.reindex` field updated to simplify querying database. See [`dipdup.enums.ReindexingReason`](https://github.com/dipdup-net/dipdup/blob/master/src/dipdup/enums.py) class for possible values.

### Fixed

- Fixed `ReindexRequiredError` not being raised when running DipDup after reindexing was triggered.
- Fixed index config hash calculation. Hashes of existing indexes in a database will be updated during the first run.
- Fixed issue in `BigMapIndex` causing the partial loss of big map diffs.
- Fixed printing help for CLI commands.
- Fixed merging storage which contains specific nested structures.

### Improved

- Raise `DatabaseConfigurationError` exception when project models are not compatible with GraphQL.
- Another bunch of performance optimizations. Reduced DB pressure, speeded up parallel processing lots of indexes.
- Added initial set of performance benchmarks (run: `./scripts/run_benchmarks.sh`)

## [3.0.4] - 2021-10-04

### Improved

- A significant increase in indexing speed.

### Fixed

- Fixed unexpected reindexing caused by the bug in processing zero- and single-level rollbacks.
- Removed unnecessary file IO calls that could cause `PermissionError` exception in Docker environments.
- Fixed possible violation of block-level atomicity during realtime indexing.

### Changes

- Public methods of `TzktDatasource` now return immutable sequences.

## [3.0.3] - 2021-10-01

### Fixed

- Fixed processing of single-level rollbacks emitted before rolled back head.

## [3.0.2] - 2021-09-30

### Added

- Human-readable `CHANGELOG.md` 🕺
- Two new options added to `dipdup run` command:
  - `--forbid-reindexing` – raise `ReindexingRequiredError` instead of truncating database when reindexing is triggered for any reason. To continue indexing with existing database run `UPDATE dipdup_schema SET reindex = NULL;`
  - `--postpone-jobs` – job scheduler won't start until all indexes are synchronized. 

### Changed

- Migration to this version requires reindexing.
- `dipdup_index.head_id` foreign key removed. `dipdup_head` table still contains the latest blocks from Websocket received by each datasource.

### Fixed

- Removed unnecessary calls to TzKT API.
- Fixed removal of PostgreSQL extensions (`timescaledb`, `pgcrypto`) by function `truncate_database` triggered on reindex.
- Fixed creation of missing project package on `init`.
- Fixed invalid handler callbacks generated on `init`.
- Fixed detection of existing types in the project.
- Fixed race condition caused by event emitter concurrency.
- Capture unknown exceptions with Sentry before wrapping to `DipDupError`.
- Fixed job scheduler start delay.
- Fixed processing of reorg messages.

## [3.0.1] - 2021-09-24

### Added

- Added `get_quote` and `get_quotes` methods to `TzKTDatasource`.

### Fixed

- Defer spawning index datasources until initial sync is complete. It helps to mitigate some WebSocket-related crashes, but initial sync is a bit slower now.
- Fixed possible race conditions in `TzKTDatasource`.
- Start `jobs` scheduler after all indexes sync with a current head to speed up indexing.

<!-- Links -->
[keep a changelog]: https://keepachangelog.com/en/1.0.0/
[semantic versioning]: https://semver.org/spec/v2.0.0.html

<!-- Versions -->
[Unreleased]: https://github.com/dipdup-net/dipdup/compare/6.2.0...HEAD
[6.2.0]: https://github.com/dipdup-net/dipdup/compare/6.1.3...6.2.0
[6.1.3]: https://github.com/dipdup-net/dipdup/compare/6.1.2...6.1.3
[6.1.2]: https://github.com/dipdup-net/dipdup/compare/6.1.1...6.1.2
[6.1.1]: https://github.com/dipdup-net/dipdup/compare/6.1.0...6.1.1
[6.1.0]: https://github.com/dipdup-net/dipdup/compare/6.0.1...6.1.0
[6.0.1]: https://github.com/dipdup-net/dipdup/compare/6.0.0...6.0.1
[6.0.0]: https://github.com/dipdup-net/dipdup/compare/6.0.0rc2...6.0.0
[6.0.0rc2]: https://github.com/dipdup-net/dipdup/compare/6.0.0-rc1...6.0.0rc2
[6.0.0-rc1]: https://github.com/dipdup-net/dipdup/compare/5.2.5...6.0.0-rc1
[5.2.5]: https://github.com/dipdup-net/dipdup/compare/5.2.4...5.2.5
[5.2.4]: https://github.com/dipdup-net/dipdup/compare/5.2.3...5.2.4
[5.2.3]: https://github.com/dipdup-net/dipdup/compare/5.2.2...5.2.3
[5.2.2]: https://github.com/dipdup-net/dipdup/compare/5.2.1...5.2.2
[5.2.1]: https://github.com/dipdup-net/dipdup/compare/5.2.0...5.2.1
[5.2.0]: https://github.com/dipdup-net/dipdup/compare/5.1.7...5.2.0
[5.1.7]: https://github.com/dipdup-net/dipdup/compare/5.1.6...5.1.7
[5.1.6]: https://github.com/dipdup-net/dipdup/compare/5.1.5...5.1.6
[5.1.5]: https://github.com/dipdup-net/dipdup/compare/5.1.4...5.1.5
[5.1.4]: https://github.com/dipdup-net/dipdup/compare/5.1.3...5.1.4
[5.1.3]: https://github.com/dipdup-net/dipdup/compare/5.1.2...5.1.3
[5.1.2]: https://github.com/dipdup-net/dipdup/compare/5.1.1...5.1.2
[5.1.1]: https://github.com/dipdup-net/dipdup/compare/5.1.0...5.1.1
[5.1.0]: https://github.com/dipdup-net/dipdup/compare/5.0.4...5.1.0
[5.0.4]: https://github.com/dipdup-net/dipdup/compare/5.0.3...5.0.4
[5.0.3]: https://github.com/dipdup-net/dipdup/compare/5.0.2...5.0.3
[5.0.2]: https://github.com/dipdup-net/dipdup/compare/5.0.1...5.0.2
[5.0.1]: https://github.com/dipdup-net/dipdup/compare/5.0.0...5.0.1
[5.0.0]: https://github.com/dipdup-net/dipdup/compare/5.0.0-rc4...5.0.0
[5.0.0-rc4]: https://github.com/dipdup-net/dipdup/compare/5.0.0-rc3...5.0.0-rc4
[4.2.7]: https://github.com/dipdup-net/dipdup/compare/4.2.6...4.2.7
[5.0.0-rc3]: https://github.com/dipdup-net/dipdup/compare/5.0.0-rc2...5.0.0-rc3
[5.0.0-rc2]: https://github.com/dipdup-net/dipdup/compare/5.0.0-rc1...5.0.0-rc2
[5.0.0-rc1]: https://github.com/dipdup-net/dipdup/compare/4.2.6...5.0.0-rc1
[4.2.6]: https://github.com/dipdup-net/dipdup/compare/4.2.5...4.2.6
[4.2.5]: https://github.com/dipdup-net/dipdup/compare/4.2.4...4.2.5
[4.2.4]: https://github.com/dipdup-net/dipdup/compare/4.2.3...4.2.4
[4.2.3]: https://github.com/dipdup-net/dipdup/compare/4.2.2...4.2.3
[4.2.2]: https://github.com/dipdup-net/dipdup/compare/4.2.1...4.2.2
[4.2.1]: https://github.com/dipdup-net/dipdup/compare/4.2.0...4.2.1
[4.2.0]: https://github.com/dipdup-net/dipdup/compare/4.1.2...4.2.0
[4.1.2]: https://github.com/dipdup-net/dipdup/compare/4.1.1...4.1.2
[4.1.1]: https://github.com/dipdup-net/dipdup/compare/4.1.0...4.1.1
[4.1.0]: https://github.com/dipdup-net/dipdup/compare/4.0.5...4.1.0
[4.0.5]: https://github.com/dipdup-net/dipdup/compare/4.0.4...4.0.5
[4.0.4]: https://github.com/dipdup-net/dipdup/compare/4.0.3...4.0.4
[4.0.3]: https://github.com/dipdup-net/dipdup/compare/4.0.2...4.0.3
[4.0.2]: https://github.com/dipdup-net/dipdup/compare/4.0.1...4.0.2
[4.0.1]: https://github.com/dipdup-net/dipdup/compare/4.0.0...4.0.1
[4.0.0]: https://github.com/dipdup-net/dipdup/compare/4.0.0-rc3...4.0.0
[4.0.0-rc3]: https://github.com/dipdup-net/dipdup/compare/4.0.0-rc2...4.0.0-rc3
[4.0.0-rc2]: https://github.com/dipdup-net/dipdup/compare/4.0.0-rc1...4.0.0-rc2
[4.0.0-rc1]: https://github.com/dipdup-net/dipdup/compare/3.1.3...4.0.0-rc1
[3.1.3]: https://github.com/dipdup-net/dipdup/compare/3.1.2...3.1.3
[3.1.2]: https://github.com/dipdup-net/dipdup/compare/3.1.1...3.1.2
[3.1.1]: https://github.com/dipdup-net/dipdup/compare/3.1.0...3.1.1
[3.1.0]: https://github.com/dipdup-net/dipdup/compare/3.0.4...3.1.0
[3.0.4]: https://github.com/dipdup-net/dipdup/compare/3.0.3...3.0.4
[3.0.3]: https://github.com/dipdup-net/dipdup/compare/3.0.2...3.0.3
[3.0.2]: https://github.com/dipdup-net/dipdup/compare/3.0.1...3.0.2
[3.0.1]: https://github.com/dipdup-net/dipdup/compare/3.0.0...3.0.1
[3.0.0]: https://github.com/dipdup-net/dipdup/releases/tag/3.0.0
