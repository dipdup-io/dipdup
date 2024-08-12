# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], and this project adheres to [Semantic Versioning].

## [8.0.0] - ????-??-??

This release contains no changes except for the version number.

## [8.0.0b5] - 2024-08-09

### Added

- package: Added built-in `batch` handler to modify higher-level indexing logic.

### Fixed

- cli: Fixed progress estimation when there are indexes with `last_level` option set.
- cli: Don't save reports for successful test runs.
- database: Fixed concurrency issue when using `get_or_create` method.
- evm: Fixed crash when contract ABI contains overloaded methods.
- tezos.operations: Fixed `sr_cement` operation index subscription.

### Changed

- config: When filtering EVM transactions by signature, use `signature` field instead of `method`.
- context: Signatures of `fire_handler` and `fire_hook` methods have changed.
- context: `ctx.logger` is a regular `logging.Logger` instead of pre-configured `FormattedLogger`.

### Other

- deps: Use `uvloop` to improve asyncio performance.

## [8.0.0b4] - 2024-07-20

### Added

- config: Publish JSON schemas for config validation and autocompletion.
- starknet.node: Added Starknet node datasource for last mile indexing.
- tezos.operations: Added `sr_cement` operation type to process Smart Rollup Cemented Commitments.

### Fixed

- evm.events: Improve fetching event batches from node.
- models: Fixed `CachedModel` preloading.

## [7.5.9] - 2024-07-20

### Fixed

- evm.events: Improve fetching event batches from node.
- models: Fixed `CachedModel` preloading.

## [8.0.0b3] - 2024-07-04

### Added

- env: Added `DIPDUP_LOW_MEMORY` variable to reduce the size of caches and buffers.

### Fixed

- cli: Fixed `--pre` installer flag.
- cli: Import some dependencies on demand to reduce memory footprint.
- evm.subsquid: Fixed typo in `iter_events` method name.

## [7.5.8] - 2024-07-04

### Fixed

- deps: Removed `pyarrow` from dependencies, bumped `web3`.
- project: Fixed `make image` target command.

## [8.0.0b2] - 2024-06-27

### Added

- env: Added `DIPDUP_JSON_LOG` environment variable to enable JSON logging.
- cli: Added `--pre` flag to `self` group commands to install pre-release versions.

### Fixed

- config: Allow `sentry.dsn` to be empty string.
- models: Fixed setting default value for `Meta.maxsize`.
- starknet.events: Fixed filtering events by key.

## [8.0.0b1] - 2024-06-19

### Added

- cli: Added full project migration support for 3.0 spec.
- starknet.events: Added `starknet.events` index kind to process Starknet events.
- starknet.subsquid: Added `starknet.subsquid` datasource to fetch historical data from Subsquid Archives.

### Fixed

- cli: Fixed errors raised when the project package is invalid.
- config: Fixed setting logging levels according to the config.
- evm.events: Fixed matching logs when filtering by topic0.

### Other

- deps: `tortoise-orm` updated to 0.21.2.

## [7.5.7] - 2024-05-30

### Fixed

- config: Fixed setting logging levels according to the config.
- evm.subsquid.events: Fixed matching logs when filtering by topic0.

## [7.5.6] - 2024-05-16

### Fixed

- cli: Improved logging of indexer status.
- performance: Fixed estimation indexing speed in levels per second.

### Changed

- api: `/performance` endpoint response format has been changed.
- performance: All time intervals are now measured in seconds.
- performance: Several metrics have been renamed and new ones have been added.

## [8.0.0a1] - 2024-05-06

### Added

- cli: Added spec_version 3.0 support to `migrate` command.
- cli: Added `package verify` command to check the package consistency.
- cli: Added `--raw` option to `config export` command to dump config preserving the original structure.
- env: Added `DIPDUP_PACKAGE_PATH` environment variable to override discovered package path.

### Fixed

- cli: Improved logging of indexer status.
- config: Fixed (de)serialization of hex strings in config.
- performance: Fixed estimation indexing speed in levels per second.
- yaml: Fixed indentation and formatting of generated YAML files.

### Changed

- api: `/performance` endpoint response format has been changed.
- config: Index kinds have been renamed and grouped by the network.
- config: Index configs accept `datasources` list instead of `datasource` field.
- config: Index template values now can be any JSON-serializable object.
- deps: Python 3.12 is now required to run DipDup.
- performance: All time intervals are now measured in seconds.
- performance: Several metrics have been renamed and new ones have been added.

### Removed

- config: `node_only` index config flag has been removed; add `evm.node` datasource(s) to the `datasources` list instead.
- config: `abi` index config field has been removed; add `abi.etherscan` datasource(s) to the `datasources` list instead.

### Other

- demos: Demo projects have been renamed to reflect the new config structure.
- deps: `datamodel-code-generator` updated to 0.25.
- deps: `pyarrow` updated to 16.0.
- deps: `pydantic` updated to 2.2.
- deps: `sentry-sdk` updated to 2.1.
- deps: `tortoise-orm` updated to 0.20.1.
- deps: `web3` updated to 6.18.

## [7.5.5] - 2024-04-17

### Added

- evm.subsquid: `evm.node` datasources can be used as index datasources.

## [7.5.4] - 2024-04-09

### Fixed

- config: Don't raise `ConfigurationError` from some model validators.
- config: Fixed crash when database path is relative and nested.
- config: Fixed issue with `from` filter being ignored.
- config: Forbid extra arguments in config mappings.

## [7.5.3] - 2024-03-28

### Fixed

- tezos.tzkt.operations: Fixed missing operations when handler pattern contains item without entrypoint.

## [7.5.2] - 2024-03-20

### Fixed

- evm.node: Fixed updating `dipdup_head` table when head block is received.
- tezos.tzkt.operations: Fixed crash when handler definition contains optional items.

## [7.5.1] - 2024-03-17

### Fixed

- evm.node: Fixed default ratelimit sleep time being too high.
- evm.subsquid.transactions: Fixed issue with `node_only` flag ignored.

### Performance

- evm.subsquid: Dynamically adjust the batch size when syncing with node.

## [7.5.0] - 2024-03-08

### Added

- config: Added `http.polling_interval` option to set the interval between polling requests (some datasources).
- hasura: Allow `bulk` request type in custom metadata files.

### Fixed

- abi.etherscan: Raise `AbiNotAvailableError` when contract is not verified.
- cli: Fixed incorrect indexer status logging.
- evm.node: Fixed memory leak when using realtime subscriptions.
- evm.node: Fixed processing chain reorgs.
- evm.node: Respect `http.batch_size` when fetching block headers.

### Performance

- hasura: Apply table customizations in a single request.
- performance: Collect hit/miss stats for cached models.
- performance: Decrease main loop and node polling intervals.
- performance: Drop caches when all indexes have reached realtime.

## [6.5.16] - 2024-03-07

This is the last release in the 6.5 branch. Please update to 7.x to get the latest features and bug fixes.

### Fixed

- tzkt: Don't use deprecated `/events` WebSockets endpoint.

### Other

- deps: Updated pytezos to 3.11.3.
- metadata: Added `oxfordnet` to supported networks.

## [7.4.0] - 2024-02-20

### Added

- cli: Added `--template` option to `new` command to skip template selection.
- evm.subsquid.transactions: Added `evm.subsquid.transactions` index kind to process EVM transactions.

### Fixed

- cli: Fixed crash when running `init` command with a config outside of the project directory.
- codegen: Don't create intermediate `events.json` file in ABI directory.
- evm.subsquid: When request to worker fails, ask router for another one instead of retrying the same worker.

## [7.3.2] - 2024-02-06

### Added

- env: Added `DIPDUP_NO_VERSION_CHECK` and `DIPDUP_NO_SYMLINK` variables.

### Fixed

- cli: Do not consider config as oneshot if `tezos.tzkt.head` index is present.
- codegen: Allow dots to be used in typenames indicating nested packages.
- evm.node: Make `withdrawals_root` field optional in `EvmNodeHeadData` model.
- http: Fixed crash on some datasource URLs.

### Performance

- evm.subsquid.events: Increase indexing speed when using EVM node.

## [7.3.1] - 2024-01-29

### Fixed

- codegen: Always cleanup jsonschemas before generating types.
- config: Make `ws_url` field optional for `evm.node` datasource.

## [7.3.0] - 2024-01-23

### Added

- tezos.tzkt.operations: Added new operation type `sr_execute` for Etherlink smart rollups.

### Fixed

- abi.etherscan: Fixed handling "rate limit reached" errors.
- cli: Fixed setting logger levels based on config and env variables.
- http: Fixed incorrect number of retries performed on failed requests.

## [7.2.2] - 2023-12-27

### Fixed

- evm.subsquid: Last mile indexing is significantly faster now.
- tezos.tzkt: Fixed an issue with approving schema after reindexing triggered by rollback.

## [7.2.1] - 2023-12-12

### Added

- cli: Added `DIPDUP_CONFIG` and `DIPDUP_ENV_FILE` environment variables corresponding to `--config` and `--env-file` options.

### Fixed

- evm.node: Fixed crash on anonymous event logs during the last mile indexing.
- evm.node: Raise an exception when no realtime messages have been received in `http.connection_timeout` seconds.

## [6.5.15] - 2023-12-01

### Other

- deps: Updated pytezos to 3.10.3.

## [7.2.0] - 2023-11-30

### Added

- api: Added HTTP API to manage a running indexer.
- config: Added `http.request_timeout` option to set the total timeout for HTTP requests.
- evm.subsquid: Added Prometheus metrics required for Subsquid Cloud deployments.
- project: Added optional `package_manager` field to replay config.
- project: Added Makefile to the default project template (only for new projects).
- tezos.tzkt: Added support for Etherlink smart rollups (`sr1…` addresses).

### Fixed

- cli: Don't suppress uncaught exceptions when performance monitoring is disabled.
- codegen: Use datamodel-code-generator from the project's virtualenv.
- evm.node: Fixed an issue with realtime subscriptions which led to indexing being stuck in some cases.
- http: Use `request_timeout` instead of `connection_timeout` for total timeout.
- install: Don't install datamodel-code-generator as a CLI tool.
- install: Respect package manager if specified in pyproject.toml.

### Performance

- evm.subsquid.events: Request logs in batches to speed up the last mile indexing.

### Security

- deps: Updated PyArrow to 14.0.1 to fix [CVE-2023-47248](https://github.com/advisories/GHSA-5wvp-7f3h-6wmm)

## [7.1.1] - 2023-11-07

### Fixed

- cli: Fixed crash on early Python 3.11 releases.
- project: Update default Docker tag for TimescaleDB HA.

## [7.1.0] - 2023-10-27

### Added

- cli: Added `--unsafe`, `--compose`, `--internal` flags to `config env` command.
- cli: Added missing short equivalents for options in some commands.
- cli: Relative paths to be initialized now can be passed to the `init` command as arguments.
- tezos.tzkt.token_balances: Added new index.

### Fixed

- cli: Fixed `DIPDUP_DEBUG` not being applied to the package logger.
- tezos.tzkt.token_transfers: Fixed filtering transfers by token_id.

## [6.5.14] - 2023-10-20

### Fixed

- token_transfer: Fixed filtering transfers by token_id.

## [7.0.2] - 2023-10-10

### Added

- database: Added `dipdup_wipe` and `dipdup_approve` SQL functions to the schema.

### Fixed

- cli: Fixed `schema wipe` command for SQLite databases.
- tezos.tzkt: Fixed regression in `get_transactions` method pagination.

## [6.5.13] - 2023-10-10

### Fixed

- tzkt: Fixed regression in `get_transactions` method pagination.

## [7.0.1] - 2023-09-30

### Added

- env: Added `DIPDUP_DEBUG` environment variable to enable debug logging.

### Fixed

- cli: Use correct data path with timescaledb-ha Docker image.
- demos: Fixed decimal overflow in `demo_uniswap` project.
- evm.node: Fixed incorrect log request parameters.
- evm.subsquid.events: Fixed issue with determining the last level when syncing with node.
- hasura: Increated retry count for initial connection (healthcheck).

## [7.0.0] - 2023-09-25

### Fixed

- cli: Import package submodules before starting indexing to fail early on import errors.
- cli: Fixed ordering of crash reports in `report` group commands.
- evm.node: Fixed parsing topics and integers in datasource models.
- evm.subsquid.events: Fixed incorrect log request parameters.
- install: Fixed issue with interpreting user answers in some cases.
- tezos.tzkt: Fixed operation matching when contract code hash specified as a string.
- tezos.tzkt: Fixed issue with processing rollbacks while sync is in progress.
- tezos.tzkt.events: Fixed parsing contract event data.
- tezos.tzkt.operations: Fixed parsing operations with empty parameters.

## [6.5.12] - 2023-09-15

### Fixed

- tzkt: Fixed issue with processing rollbacks while sync is in progress.
- tzkt: Fixed operation matching when contract code hash specified as a string.
- tzkt: Fixed parsing contract event data.

## [7.0.0rc5] - 2023-09-06

### Fixed

- evm.subsquid: Create a separate aiohttp session for each worker.
- evm.subsquid.events: Sync to `last_level` if specified in config.
- evm.node: Set `timestamp` field to the block timestamp.

## [6.5.11] - 2023-09-02

### Fixed

- index: Fixed crash when parsing typed transactions with empty parameter.
- tzkt: Fixed pagination when requesting transactions.
- tzkt: Use cursor iteration where possible.

## [7.0.0rc4] - 2023-08-23

### Added

- models: Added optional `maxsize` meta field to `CachedModel` to limit the LRU cache size.

### Fixed

- cli: Fixed `config export --full` command showing original config.
- cli: Keep the last 100 reports only.
- cli: Fixed `schema wipe` command crash due to `dipdup_meta` table being always immune.
- config: Don't create empty SentryConfig if DSN is not set.
- context: Share internal state between context instances.
- evm.node: Fixed keepalive loop for websocket connection.
- evm.node: Fixed parsing empty realtime message payloads.
- jobs: Don't add jobs before scheduler is started.
- package: Fixed package detection for poetry managed projects.
- package: Fixed mypy command in default template.
- package: Create package symlink only when needed.

### Changed

- cli: `report` command renamed to `report ls`.

## [7.0.0rc3] - 2023-08-05

### Fixed

- ci: Fixed dipdup package metadata.
- cli: Generate base template from replay only when --base flag is set.
- cli: Remove cached jsonschemas when calling init --force.
- codegen: Filter jsonschemas by prefixes supported by code generator.
- index: Fixed crash when parsing typed transactions with empty parameter.
- index: Remove Python limitation on large int<->str conversions.
- package: Create jsonschemas directory if not exists.
- package: Don't create empty pyproject.toml during init.
- package: Fixed discovery of the package when workdir is project root.

## [6.5.10] - 2023-08-02

### Fixed

- index: Remove Python limitation on large int<->str conversions.

## [7.0.0rc2] - 2023-07-26

### Fixed

- package: Create missing files from project base on init.
- package: Update replay.yaml on init.
- demos: Don't include database config in root config.

## [7.0.0rc1] - 2023-07-21

### Added

- abi.etherscan: Added `abi.etherscan` datasource to fetch ABIs from Etherscan.
- api: Added `/performance` endpoint to request indexing stats.
- cli: Added `report` command group to manage performance and crash reports created by DipDup.
- config: Added `advanced.decimal_precision` field to overwrite precision if it's not guessed correctly based on project models.
- config: Added `advanced.unsafe_sqlite` field to disable journaling and data integrity checks.
- config: Added `advanced.api` section to configure monitoring API exposed by DipDup.
- config: Added `advanced.metrics` field to configure amount of gathered metrics.
- config: Added `http.alias` field to overwrite alias of datasource HTTP gateway.
- database: Added `dipdup_meta` immune table to store arbitrary JSON values.
- database: Added experimental support for immune tables in SQLite.
- evm.node: Added `evm.node` datasource to receive events from Ethereum node and use web3 API.
- evm.subsquid: Added `evm.subsquid` datasource to fetch historical data from Subsquid Archives.
- evm.subsquid.events: Added `evm.subsquid.events` index to process event logs from Subsquid Archives.

### Fixed

- database: Fixed `OperationalError` raised in some cases after calling `bulk_create`.
- database: Allow running project scripts and queries on SQLite.
- database: Don't cleanup model updates on every loop.

### Changed

- ci: Docker images are now based on Debian 12.
- cli: `config env --file` option renamed to `--output`.
- cli: Commands to manage local dipdup installation moved to the `self` group.
- cli: `init --overwrite-types` flag renamed to `--force` and now also affects ABIs.
- config: `advanced.rollback_depth` value set based on indexes used in the project if not set explicitly.
- config: `logging` field now can contain either loglevel or name-loglevel mapping.
- context: Signature of `add_contract` method has changed.
- database: `EnumField` now uses `TEXT` type instead of `VARCHAR(n)`.
- database: Querysets are no longer copied between chained method calls (`.filter().order_by().limit()`)
- database: Store datasource aliases instead of URLs in `dipdup_head` table.
- models: User models must use field classes from `dipdup.fields` module instead of `tortoise.fields`.
- tezos.tzkt: Signatures of `[get/iter]_similar_contracts` and `[get/iter]_originated_contracts` methods have changed.
- tezos.tzkt.head: Replaced `handlers` section with a single `callback` field in config.

### Removed

- ci: `-slim` and `-pytezos` Docker images are no longer published.
- ci: Docker images no longer contain git, poetry and custom scripts.
- cli: Removed `dipdup-install` alias to `dipdup.install`.
- cli: Removed `status` command.
- config: Removed `similar_to` filter of `operation` index pattern.
- config: Removed `# dipdup: ignore` hint used to ignore typeclass during init.
- config: Removed `advanced.metadata_interface` flag (always enabled).
- sentry: Removed `crash_reporting` flag and built-in DSN.

### Other

- tzkt: Request plain values instead of mappings from TzKT when possible.

## [6.5.9] - 2023-07-11

### Fixed

- tzkt: Optimized queries for `operation_unfiltered` index.

## [6.5.8] - 2023-06-28

### Fixed

- cli: Fixed `init` crash when package name is equal to one of the project typenames.

## [6.5.7] - 2023-05-30

### Added

- config: Added `advanced.decimal_precision` option to adjust decimal context precision.

### Fixed

- database: Fixed `OperationalError` raised in some cases after calling `bulk_create`.
- database: Allow running project scripts and queries on SQLite. 
- database: Don't cleanup model updates on every loop.
- http: Mark `asyncio.TimeoutError` exception as safe to retry.

### Other

- http: Deserialize JSON responses with `orjson`.

## [6.5.6] - 2023-05-02

### Fixed

- config: Fixed crash due to incorrect parsing of `event` index definitions.
- http: Fixed waiting for response indefinitely when IPFS hash is not available.

### Other

- ci: Slim Docker image updated to Alpine 3.17.
- metadata: Added `nairobinet` to supported networks.

## [6.5.5] - 2023-04-17

### Fixed

- config: Enable early realtime mode when config contains bigmap indexes with `skip_history`.
- http: Fixed crash when using custom datasources.
- index: Allow mixing `source` and `entrypoint` filters in `operation` index pattern.

### Other

- ci: Default git branch switched to `next`.

## [6.5.4] - 2023-03-31

### Fixed

- config: Fixed incorrest parsing of `token_transfer` index filters. 

### Other

- deps: Updated pytezos to 3.9.0.

## [6.5.3] - 2023-03-28

### Fixed

- cli: Don't enforce logging `DeprecationWarning` warnings.
- cli: Fixed `BrokenPipeError` messages when interrupting with DipDup with SIGINT.
- config: Fixed crash when `token_transfer` index has `from` or `to` filter.

### Security

- hasura: Forbid using Hasura instances affected by [GHSA-c9rw-rw2f-mj4x](https://github.com/hasura/graphql-engine/security/advisories/GHSA-c9rw-rw2f-mj4x).

## [6.5.2] - 2023-03-09

### Fixed

- codegen: Fixed type generation for contracts with "default" entrypoint.
- metadata: Add "mumbainet" to available networks.
- sentry: Fixed bug leading to crash reports not being sent in some cases.
- sentry: Fixed crash report grouping.

### Deprecated

- ci: `-slim` images will be based on Ubuntu instead of Alpine in the next major release.

## [6.5.1] - 2023-02-21

### Fixed

- codegen: Fixed bug leading to incorrect imports in generated callbacks in some cases.
- codegen: Fixed validation of created package after `dipdup init`.
- config: Allow using empty string as default env (`{DEFAULT_EMPTY:-}`).

### Other

- deps: Updated pydantic to 1.10.5
- deps: Updated datamodel-code-generator to 0.17.1
- deps: Updated tortoise-orm to 0.19.3
- deps: Updated pytezos to 3.8.0

## [6.5.0] - 2023-01-28

### Added

- hasura: Apply arbitrary metadata from `hasura` project directory.
- config: Added `allow_inconsistent_metadata` option to `hasura` section.

### Fixed

- config: Do not include coinbase datasource credentials in config repr.
- database: Fixed crash when schema generation should fail with `schema_modified`.
- hasura: Stop using deprecated schema/metadata API.
- index: Fixed unnecessary prefetching of migration originations in `operation` index.
- index: Remove disabled indexes from the dispatcher queue.
- sentry: Flush and reopen session daily.
- tzkt: Fixed `OperationData.type` field value for migration originations.
- tzkt: Added missing `last_level` argument to migration origination fetching methods.

### Other

- tzkt: Updated current testnet protocol (`limanet`).
- deps: Updated asyncpg to 0.27.0
- deps: Updated hasura to 2.17.0

## [6.4.3] - 2023-01-05

### Fixed

- context: Fixed order of `add_contract` method arguments.
- index: Fixed matching operations when both `address` and `code_hash` filters are specified.
- sentry: Fixed sending crash reports when DSN is not set implicitly.
- sentry: Increase event length limit.

## [6.4.2] - 2022-12-31

### Added

- config: Added `http.ratelimit_sleep` option to set fixed sleep time on 429 responses.
- context: Allow adding contracts by code hash in runtime.

### Fixed

- http: Fixed merging user-defined HTTP settings and datasource defaults.
- tzkt: Fixed iterating over big map keys.

## [6.4.1] - 2022-12-22

### Fixed

- models: Fixed package model detection.

## [6.4.0] - 2022-12-20

### Fixed

- cli: `update` and `uninstall` commands no longer require a valid config.
- cli: Fixed a regression in `new` command leading to crash with `TypeError`.
- config: Fixed `jobs` section deserialization.
- database: Ignore abstract models during module validation.

## [6.4.0rc1] - 2022-12-09

### Added

- config: Added optional `code_hash` field to contract config.
- context: Added `first_level` and `last_level` arguments to `ctx.add_index` methods.
- index: Filtering by `code_hash` is available for `operation` index.
- tzkt: Added datasource methods `get_contract_address` and `get_contract_hashes`.
- tzkt: Originations and operations now can be fetched by contract code hashes.
- tzkt: Added `sender_code_hash` and `target_code_hash` fields to `OperationData` model.

### Fixed

- codegen: Unresolved index templates are now correctly processed during types generation.
- demos: Fixed outdated `demo_dao` project.
- http: Fixed a crash when datasource URL contains trailing slash.
- metadata: Add `limanet` to supported networks.
- projects: Do not scaffold an outdated `poetry.lock`.

### Changed

- demos: Demos were renamed to better indicate their purpose.
- exceptions: `FrameworkException` is raised instead of plain `RuntimeError` when a framework error occurs.
- exceptions: Known exceptions are inherited from `FrameworkError`.
- tzkt: Some datasource methods have changed their signatures.

### Deprecated

- config: `similar_to.address` filter is an alias for `originated_contract.code_hash` and will be removed in the next major release.
- config: `DipDupError` is an alias for `FrameworkError` and will be removed in the next major release.

## [6.3.1] - 2022-11-25

### Fixed

- cli: Do not apply cli hacks on module import.
- codegen: Include PEP 561 marker in generated packages.
- codegen: Untyped originations are now correctly handled.
- codegen: Fixed `alias` config field having no effect on originations.
- codegen: Fixed optional arguments in generated callbacks.
- config: Suggest snake_case for package name.
- config: Fixed crash with `RuntimeError` when index has no subscriptions.
- http: Limit aiohttp sessions to specific base URL.
- index: Do not deserialize originations matched by the `source` filter.
- index: Wrap storage deserialization exceptions with `InvalidDataError`.
- projects: Fixed Hasura environment in docker-compose examples.

### Security

- hasura: Forbid using Hasura instances running vulnerable versions ([GHSA-g7mj-g7f4-hgrg](https://github.com/hasura/graphql-engine/security/advisories/GHSA-g7mj-g7f4-hgrg))

### Other

- ci: `mypy --strict` is now enforced on a codebase.
- ci: Finished migration to `pytest`.

## [6.3.0] - 2022-11-15

### Added

- context: Added `execute_sql_query` method to run queries from `sql` project directory.
- context: `execute_sql` method now accepts arbitrary arguments to format SQL script (unsafe, use with caution).
- index: New filters for `token_transfer` index.

### Fixed

- cli: Fixed missing log messages from `ctx.logger`.
- codegen: Better PEP 8 compatibility of generated callbacks.
- context: Fixed SQL scripts executed in the wrong order.
- context: Fixed `execute_sql` method crashes when the path is not a directory.
- database: Fixed crash with `CannotConnectNowError` before establishing the database connection.
- database: Fixed crash when using F expressions inside versioned transactions.
- http: Fixed caching datasource responses when `replay_path` contains tilde.
- http: Adjusted per-datasource default config values.
- project: Use the latest stable version instead of hardcoded values.
- tzkt: Fixed deserializing of `EventData` and `OperationData` models.
- tzkt: Fixed matching migration originations by address.

### Deprecated

- ci: `pytezos` extra and corresponding Docker image are deprecated. 

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

### Changed

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

- New index class `HeadIndex` (configuration: [`dipdup.config.HeadIndexConfig`](https://github.com/dipdup-io/dipdup/blob/master/src/dipdup/config.py#L778)). Use this index type to handle head (limited block header content) updates. This index type is realtime-only: historical data won't be indexed during the synchronization stage.
- Added three new commands: `schema approve`, `schema wipe`, and `schema export`. Run `dipdup schema --help` command for details.

### Changed

- Triggering reindexing won't lead to dropping the database automatically anymore. `ReindexingRequiredError` is raised instead. `--forbid-reindexing` option has become default.
- `--reindex` option is removed. Use `dipdup schema wipe` instead.
- Values of `dipdup_schema.reindex` field updated to simplify querying database. See [`dipdup.enums.ReindexingReason`](https://github.com/dipdup-io/dipdup/blob/master/src/dipdup/enums.py) class for possible values.

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
[Unreleased]: https://github.com/dipdup-io/dipdup/compare/8.0.0...HEAD
[8.0.0]: https://github.com/dipdup-io/dipdup/compare/8.0.0b5...8.0.0
[8.0.0b5]: https://github.com/dipdup-io/dipdup/compare/8.0.0b4...8.0.0b5
[8.0.0b4]: https://github.com/dipdup-io/dipdup/compare/8.0.0b3...8.0.0b4
[8.0.0b3]: https://github.com/dipdup-io/dipdup/compare/8.0.0b2...8.0.0b3
[7.5.8]: https://github.com/dipdup-io/dipdup/compare/7.5.7...7.5.8
[8.0.0b2]: https://github.com/dipdup-io/dipdup/compare/8.0.0b1...8.0.0b2
[8.0.0b1]: https://github.com/dipdup-io/dipdup/compare/8.0.0a1...8.0.0b1
[7.5.7]: https://github.com/dipdup-io/dipdup/compare/7.5.6...7.5.7
[7.5.6]: https://github.com/dipdup-io/dipdup/compare/7.5.5...7.5.6
[8.0.0a1]: https://github.com/dipdup-io/dipdup/compare/7.5.7...8.0.0a1
[7.5.5]: https://github.com/dipdup-io/dipdup/compare/7.5.4...7.5.5
[7.5.4]: https://github.com/dipdup-io/dipdup/compare/7.5.3...7.5.4
[7.5.3]: https://github.com/dipdup-io/dipdup/compare/7.5.2...7.5.3
[7.5.2]: https://github.com/dipdup-io/dipdup/compare/7.5.1...7.5.2
[7.5.1]: https://github.com/dipdup-io/dipdup/compare/7.5.0...7.5.1
[7.5.0]: https://github.com/dipdup-io/dipdup/compare/7.4.0...7.5.0
[6.5.16]: https://github.com/dipdup-io/dipdup/compare/6.5.15...6.5.16
[7.4.0]: https://github.com/dipdup-io/dipdup/compare/7.3.2...7.4.0
[7.3.2]: https://github.com/dipdup-io/dipdup/compare/7.3.1...7.3.2
[7.3.1]: https://github.com/dipdup-io/dipdup/compare/7.3.0...7.3.1
[7.3.0]: https://github.com/dipdup-io/dipdup/compare/7.2.2...7.3.0
[7.2.2]: https://github.com/dipdup-io/dipdup/compare/7.2.1...7.2.2
[7.2.1]: https://github.com/dipdup-io/dipdup/compare/7.2.0...7.2.1
[6.5.15]: https://github.com/dipdup-io/dipdup/compare/6.5.14...6.5.15
[7.2.0]: https://github.com/dipdup-io/dipdup/compare/7.1.1...7.2.0
[7.1.1]: https://github.com/dipdup-io/dipdup/compare/7.1.0...7.1.1
[7.1.0]: https://github.com/dipdup-io/dipdup/compare/7.0.2...7.1.0
[6.5.14]: https://github.com/dipdup-io/dipdup/compare/6.5.13...6.5.14
[7.0.2]: https://github.com/dipdup-io/dipdup/compare/7.0.1...7.0.2
[6.5.13]: https://github.com/dipdup-io/dipdup/compare/6.5.12...6.5.13
[7.0.1]: https://github.com/dipdup-io/dipdup/compare/7.0.0...7.0.1
[7.0.0]: https://github.com/dipdup-io/dipdup/compare/7.0.0rc5...7.0.0
[6.5.12]: https://github.com/dipdup-io/dipdup/compare/6.5.11...6.5.12
[7.0.0rc5]: https://github.com/dipdup-io/dipdup/compare/7.0.0rc4...7.0.0rc5
[6.5.11]: https://github.com/dipdup-io/dipdup/compare/6.5.10...6.5.11
[7.0.0rc4]: https://github.com/dipdup-io/dipdup/compare/7.0.0rc3...7.0.0rc4
[7.0.0rc3]: https://github.com/dipdup-io/dipdup/compare/7.0.0rc2...7.0.0rc3
[6.5.10]: https://github.com/dipdup-io/dipdup/compare/6.5.9...6.5.10
[7.0.0rc2]: https://github.com/dipdup-io/dipdup/compare/7.0.0rc1...7.0.0rc2
[7.0.0rc1]: https://github.com/dipdup-io/dipdup/compare/6.5.9...7.0.0rc1
[6.5.9]: https://github.com/dipdup-io/dipdup/compare/6.5.8...6.5.9
[6.5.8]: https://github.com/dipdup-io/dipdup/compare/6.5.7...6.5.8
[6.5.7]: https://github.com/dipdup-io/dipdup/compare/6.5.6...6.5.7
[6.5.6]: https://github.com/dipdup-io/dipdup/compare/6.5.5...6.5.6
[6.5.5]: https://github.com/dipdup-io/dipdup/compare/6.5.4...6.5.5
[6.5.4]: https://github.com/dipdup-io/dipdup/compare/6.5.3...6.5.4
[6.5.3]: https://github.com/dipdup-io/dipdup/compare/6.5.2...6.5.3
[6.5.2]: https://github.com/dipdup-io/dipdup/compare/6.5.1...6.5.2
[6.5.1]: https://github.com/dipdup-io/dipdup/compare/6.5.0...6.5.1
[6.5.0]: https://github.com/dipdup-io/dipdup/compare/6.4.3...6.5.0
[6.4.3]: https://github.com/dipdup-io/dipdup/compare/6.4.2...6.4.3
[6.4.2]: https://github.com/dipdup-io/dipdup/compare/6.4.1...6.4.2
[6.4.1]: https://github.com/dipdup-io/dipdup/compare/6.4.0...6.4.1
[6.4.0]: https://github.com/dipdup-io/dipdup/compare/6.4.0rc1...6.4.0
[6.4.0rc1]: https://github.com/dipdup-io/dipdup/compare/6.3.1...6.4.0rc1
[6.3.1]: https://github.com/dipdup-io/dipdup/compare/6.3.0...6.3.1
[6.3.0]: https://github.com/dipdup-io/dipdup/compare/6.2.0...6.3.0
[6.2.0]: https://github.com/dipdup-io/dipdup/compare/6.1.3...6.2.0
[6.1.3]: https://github.com/dipdup-io/dipdup/compare/6.1.2...6.1.3
[6.1.2]: https://github.com/dipdup-io/dipdup/compare/6.1.1...6.1.2
[6.1.1]: https://github.com/dipdup-io/dipdup/compare/6.1.0...6.1.1
[6.1.0]: https://github.com/dipdup-io/dipdup/compare/6.0.1...6.1.0
[6.0.1]: https://github.com/dipdup-io/dipdup/compare/6.0.0...6.0.1
[6.0.0]: https://github.com/dipdup-io/dipdup/compare/6.0.0rc2...6.0.0
[6.0.0rc2]: https://github.com/dipdup-io/dipdup/compare/6.0.0-rc1...6.0.0rc2
[6.0.0-rc1]: https://github.com/dipdup-io/dipdup/compare/5.2.5...6.0.0-rc1
[5.2.5]: https://github.com/dipdup-io/dipdup/compare/5.2.4...5.2.5
[5.2.4]: https://github.com/dipdup-io/dipdup/compare/5.2.3...5.2.4
[5.2.3]: https://github.com/dipdup-io/dipdup/compare/5.2.2...5.2.3
[5.2.2]: https://github.com/dipdup-io/dipdup/compare/5.2.1...5.2.2
[5.2.1]: https://github.com/dipdup-io/dipdup/compare/5.2.0...5.2.1
[5.2.0]: https://github.com/dipdup-io/dipdup/compare/5.1.7...5.2.0
[5.1.7]: https://github.com/dipdup-io/dipdup/compare/5.1.6...5.1.7
[5.1.6]: https://github.com/dipdup-io/dipdup/compare/5.1.5...5.1.6
[5.1.5]: https://github.com/dipdup-io/dipdup/compare/5.1.4...5.1.5
[5.1.4]: https://github.com/dipdup-io/dipdup/compare/5.1.3...5.1.4
[5.1.3]: https://github.com/dipdup-io/dipdup/compare/5.1.2...5.1.3
[5.1.2]: https://github.com/dipdup-io/dipdup/compare/5.1.1...5.1.2
[5.1.1]: https://github.com/dipdup-io/dipdup/compare/5.1.0...5.1.1
[5.1.0]: https://github.com/dipdup-io/dipdup/compare/5.0.4...5.1.0
[5.0.4]: https://github.com/dipdup-io/dipdup/compare/5.0.3...5.0.4
[5.0.3]: https://github.com/dipdup-io/dipdup/compare/5.0.2...5.0.3
[5.0.2]: https://github.com/dipdup-io/dipdup/compare/5.0.1...5.0.2
[5.0.1]: https://github.com/dipdup-io/dipdup/compare/5.0.0...5.0.1
[5.0.0]: https://github.com/dipdup-io/dipdup/compare/5.0.0-rc4...5.0.0
[5.0.0-rc4]: https://github.com/dipdup-io/dipdup/compare/5.0.0-rc3...5.0.0-rc4
[4.2.7]: https://github.com/dipdup-io/dipdup/compare/4.2.6...4.2.7
[5.0.0-rc3]: https://github.com/dipdup-io/dipdup/compare/5.0.0-rc2...5.0.0-rc3
[5.0.0-rc2]: https://github.com/dipdup-io/dipdup/compare/5.0.0-rc1...5.0.0-rc2
[5.0.0-rc1]: https://github.com/dipdup-io/dipdup/compare/4.2.6...5.0.0-rc1
[4.2.6]: https://github.com/dipdup-io/dipdup/compare/4.2.5...4.2.6
[4.2.5]: https://github.com/dipdup-io/dipdup/compare/4.2.4...4.2.5
[4.2.4]: https://github.com/dipdup-io/dipdup/compare/4.2.3...4.2.4
[4.2.3]: https://github.com/dipdup-io/dipdup/compare/4.2.2...4.2.3
[4.2.2]: https://github.com/dipdup-io/dipdup/compare/4.2.1...4.2.2
[4.2.1]: https://github.com/dipdup-io/dipdup/compare/4.2.0...4.2.1
[4.2.0]: https://github.com/dipdup-io/dipdup/compare/4.1.2...4.2.0
[4.1.2]: https://github.com/dipdup-io/dipdup/compare/4.1.1...4.1.2
[4.1.1]: https://github.com/dipdup-io/dipdup/compare/4.1.0...4.1.1
[4.1.0]: https://github.com/dipdup-io/dipdup/compare/4.0.5...4.1.0
[4.0.5]: https://github.com/dipdup-io/dipdup/compare/4.0.4...4.0.5
[4.0.4]: https://github.com/dipdup-io/dipdup/compare/4.0.3...4.0.4
[4.0.3]: https://github.com/dipdup-io/dipdup/compare/4.0.2...4.0.3
[4.0.2]: https://github.com/dipdup-io/dipdup/compare/4.0.1...4.0.2
[4.0.1]: https://github.com/dipdup-io/dipdup/compare/4.0.0...4.0.1
[4.0.0]: https://github.com/dipdup-io/dipdup/compare/4.0.0-rc3...4.0.0
[4.0.0-rc3]: https://github.com/dipdup-io/dipdup/compare/4.0.0-rc2...4.0.0-rc3
[4.0.0-rc2]: https://github.com/dipdup-io/dipdup/compare/4.0.0-rc1...4.0.0-rc2
[4.0.0-rc1]: https://github.com/dipdup-io/dipdup/compare/3.1.3...4.0.0-rc1
[3.1.3]: https://github.com/dipdup-io/dipdup/compare/3.1.2...3.1.3
[3.1.2]: https://github.com/dipdup-io/dipdup/compare/3.1.1...3.1.2
[3.1.1]: https://github.com/dipdup-io/dipdup/compare/3.1.0...3.1.1
[3.1.0]: https://github.com/dipdup-io/dipdup/compare/3.0.4...3.1.0
[3.0.4]: https://github.com/dipdup-io/dipdup/compare/3.0.3...3.0.4
[3.0.3]: https://github.com/dipdup-io/dipdup/compare/3.0.2...3.0.3
[3.0.2]: https://github.com/dipdup-io/dipdup/compare/3.0.1...3.0.2
[3.0.1]: https://github.com/dipdup-io/dipdup/compare/3.0.0...3.0.1
[3.0.0]: https://github.com/dipdup-io/dipdup/releases/tag/3.0.0
