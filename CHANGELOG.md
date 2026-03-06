# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], and this project adheres to [Semantic Versioning].

Releases prior to 7.0 has been removed from this file to declutter search results; see the [archived copy](https://github.com/dipdup-io/dipdup/blob/8.0.0b5/CHANGELOG.md) for the full list.

## [Unreleased]

### Fixed

- cli: Fixed crash when running `schema wipe` on empty or in-memory database.
- database: Fixed `dipdup_wipe` function not dropping all user-defined objects in some cases.
- database: Fix exception when creating connections with aiosqlite==0.22.0.

## [8.5.1] - 2025-11-03

### Fixed

- demos: Use Etherscan v2 API endpoints in EVM templates.
- mcp: Fixed crash when using `mcp.tool` decorator.
- evm.node: Respect `http.batch_size` when fetching events and transactions.

### Changed

- cli: Don't notify about new framework versions available.

## [8.5.0] - 2025-09-14

### Added

- database: Support running multiple indexers on different schemas in the same database.
- env: Added `DIPDUP_NO_HOOKS` environment variable to temporary disable internal and user-defined hooks.
- env: Added debugpy support to connect to the running indexer; enable with `DIPDUP_DEBUG` environment variable.
- hasura: Extract table/field descriptions from models' docstrings and apply as database comments.

### Fixed

- config: Fixed detection of missing env variables.
- database: Fixed `dipdup_wipe` function affecting non-public tables.
- package: Fixed incorrect package name in replay files.
- substrate.events: Fixed fetching events with node datasource.
- tezos: Fixed parsing payload when model class has been modified.
- tezos.operations: Fixed missing migration originations when enabled in `types` filter.

### Changed

- env: Autodetected variables `DIPDUP_CI` and `DIPDUP_DOCKER` have been replaced with `env.is_in_gha`, `env.is_in_docker` helpers.
- http: Randomize ratelimit sleep time in 10% range.

## [8.4.3] - 2025-08-13

### Fixed

- tezos.tzkt: Updated models to match 1.16 version of API (Seoulnet).

## [8.4.2] - 2025-06-18

### Added

- config: Added `realtime` flag to datasource config to enable websockets/polling implicitly.

### Fixed

- cli: Skip logging indexer status if it has not changed.
- config: Fixed `config export` command crash when `advanced.reindex` section is present in config.
- config: Do not trigger `config_modified` reindexing when datasource URLs are updated.
- datasources: Do not run datasources not linked to any index and without `realtime` flag set.
- models: Fixed serializing UUIDs in `JSONField`.
- substrate: Fixed loading type registries when specified in config.
- substrate: Fixed processing several vector types.

## [8.4.1] - 2025-06-02

### Fixed

- substrate.events: Fixed crash caused by choosing incorrect runtime metadata for decoding.

## [8.4.0] - 2025-05-20

### Added

- context: Added configurable watchdog service to notify about long-running callbacks and transactions.
- cli: Added loading env-file `dipdup.env` if presented in the current directory.
- cli: Added `-h` shorthand for `--help` option in all commands.
- cli: Added `--no-types` option to `init` command to skip generating type classes.

### Fixed

- cli: Fixed `config env -i` command output.
- cli: Fixed discovering package path.
- cli: Fixed printing help message when running commands without arguments.
- codegen: Fixed loading ABIs from the project with no ABI datasources configured.
- env: Skip detection of some variables if set explicitly.
- http: Fixed merging request URL with base path.
- project: Fixed `make image` command and default workdir.
- project: Fixed missing codegen headers in project base.
- substrate.node: Fixed event index field.

### Removed

- project: Do not generate and track `.env.default` files on init. Use `config env` command for new environments.

## [8.3.3] - 2025-04-29

### Added

- cli: Added `--name` option to `new` command to skip asking for the project name.

### Fixed

- cli: Fixed regression in `init` command behavior when run without flags.
- cli: Fixed detecting package name in existing projects without `replay.yaml` file.
- cli: Fixed `init` command processing the same paths multiple times.
- cli: Fixed `init` command not respecting `--force` flag when generating default envfiles.

## [8.3.2] - 2025-04-17

### Added

- cli: Added `init --no-base` option to skip creating the base template.
- env: Added `DIPDUP_NO_BASE` environment variable to skip creating the base template.
- mcp: Added `ctx.api` datasource and `ctx.call_api` helper to server context.

### Fixed

- cli: Fixed `new` command using incorrect template.
- mcp: Fixed handling exceptions in MCP tools.

### Changed

- cli: `init --base` option is now enabled by default.

## [8.3.1] - 2025-04-08

### Added

- config: Added `api_url` and `compatibility` fields to MCP config.

### Fixed

- api: Fixed configuring uvicorn logging.
- api: Strip secret fields from API responses.
- cli: Fixed logging indexer status.
- mcp: Expose resources as tools for clients that don't support MCP resources yet.
- project: Fixed generation of compose manifest and configs for MCP environment.

### Changed

- api: Built-in management API is now using Starlette instead of plain aiohttp.

## [8.3.0] - 2025-04-02

### Added

- cli: Apply ruff linting and formating on init.
- mcp: Added Model Context Protocol (MCP) server implementation.
- mcp: Added built-in resources for accessing indexer configuration and metrics.
- mcp: Added support for exposing custom tools and resources via `@dipdup.mcp` decorators.

### Fixed

- package: Create package marker even if helper symlink is present.
- project: Fixed built sdist/wheel artifacts which contained unrelated files.

### Changed

- cli: `install.py` script and `dipdup self` commands use `uv tool` instead of `pipx`.
- cli: `new` command uses default values for some `replay.yaml` fields.
- project: Use `hatchling` build backend for new projects.
- project: Replace `black` with `ruff` as default formatter.

## [8.2.2] - 2025-03-13

### Added

- starknet.node: Added `fetch_block_headers` option to datasource config.

### Fixed

- evm.node: Fixed empty `gasPrice` field base conversion on evm transaction deserialization.

## [8.2.1] - 2025-02-19

### Added

- cli: Rewritten interactive mode for `new` command.
- evm.blockvision: Added `evm.blockvision` datasource to fetch ABIs from Blockvision API.
- evm.sourcify: Added `evm.sourcify` datasource to fetch ABIs from Sourcify API.

### Fixed

- coinbase: Fixed crash when using coinbase datasource.
- evm.node: Fixed crash when block range goes out of bounds.

## [8.2.0] - 2025-02-10

### Added

- starknet.node: Added methods for fetching contract ABIs for `init` command.

### Fixed

- cli: Fixed help message on `CallbackError` reporting `batch` handler instead of actual one.
- starknet: Process all data types correctly.
- starknet.node: Fetch missing block timestamp and txn id when synching with node.
- substrate.subsquid: Fixed parsing nested structures in response.
- substrate.subsquid: Fixed parsing for `__kind` junctions with multiple keys.

### Changed

- project: Set default PostgreSQL password and Hasura secret (both are `changeme`) for new projects.
- project: Use PostgreSQL 16 image for new projects.

### Deprecated

- package: DipDup packages are expected to have `pyproject.toml` and `dipdup.yaml` files in the root directory. This will become a requirement in 9.0.

### Other

- deps: `tortoise-orm` updated to 0.24.0.

## [8.2.0rc1] - 2025-01-24

### Added

- project: Support uv package manager in the default project template.
- substrate.events: Added `subtrate.events` index kind to process Substrate events.
- substrate.node: Added `subtrate.node` datasource to receive data from Substrate node.
- substrate.subscan: Added `substrate.subscan` datasource to fetch ABIs from Subscan.
- substrate.subsquid: Added `substrate.subsquid` datasource to fetch historical data from Squid Network.

### Fixed

- database: Don't process internal models twice if imported from the project.
- evm.subsquid: Fixed event/transaction model deserialization.

### Changed

- env: Database migrations with aerich require `DIPDUP_MIGRATIONS` variable to be set.
- evm.etherscan: Datasource has been renamed from `abi.etherscan` to `evm.etherscan` for consistency.
- project: Expose Prometheus and internal API ports in default sqlite environment.

## [8.1.4] - 2025-01-12

### Fixed

- evm: Fixed sending JSONRPC requests via web3.py provider.
- evm: Fixed parsing tuple types in ABI.
- evm.subsquid: Fixed type of `timestamp` field of event/transaction models.
- evm.subsquid: Fixed empty field base conversion on event deserialization.
- starknet: Fixed parsing contract addresses starting with `0x0`.

## [8.1.3] - 2024-12-20

### Fixed

- cli: Don't wrap exceptions with `CallbackError` to avoid shadowing the original exception.
- cli: Fixed `--template` option being ignored when `--quiet` flag is set.
- config: Fixed setting default loglevels when `logging` is a dict.
- config: Fixed parsing config files after updating to pydantic 2.10.3.
- config: Fixed starknet index validation error.
- metrics: Fixed indexed objects counter.
- starknet: Added support for struct and array types, as well as u256 and ByteArray handlers.
- starknet: Fixed event payload parsing (account for keys field).
- starknet: Fixed missing class property in node datasource.

## [8.1.2] - 2024-12-10

### Fixed

- context: Allow to add Starknet contracts in runtime.
- database: Ignore non-existent immutable table on schema wipe.
- starknet.events: Fixed event ID calculation.

## [8.1.1] - 2024-10-17

### Fixed

- cli: Fixed progress estimation logging.

## [8.1.0] - 2024-10-16

### Added

- evm.etherscan: Try to extract ABI from webpage when API call fails.
- cli: Added `schema` subcommands to manage database migrations: `migrate`, `upgrade`, `downgrade`, `heads` and `history`.
- cli: Added interactive mode for `new` command.
- database: Support database migrations using [`aerich`](https://github.com/tortoise/aerich).
- hasura: Added `hide` and `hide_internal` config options to make specified tables/views private.

### Fixed

- cli: Reload constants in `dipdup.env` after applying env-files.

## [8.0.0] - 2024-09-10

### Added

- cli: Added `-C` option, a shorthand for `-c . -c configs/dipdup.<name>.yaml`.
- database: Added `dipdup_status` view to the schema.

### Fixed

- cli: Don't update existing installation in `self install` command unless asked to.
- cli: Fixed env files not being loaded in some commands.
- install: Fixed reinstalling package when `--force` flag is used.
- package: Create package in-place if cwd equals package name.
- performance: Add index name to fetcher and realtime queues.
- subsquid: Fixed missing entry in `dipdup_head` internal table.
- tezos.big_maps: Fixed logging status message in `skip_history` mode.
- tezos.big_maps: Respect order of handlers in `skip_history` mode.

### Removed

- config: Removed `advanced.skip_version_check` flag; use `DIPDUP_NO_VERSION_CHECK` environment variable.
- database: Removed `dipdup_head_status` view; use `dipdup_status` view instead.

### Performance

- database: Set `synchronous=NORMAL` and `journal_mode=WAL` pragmas for on-disk SQLite databases.

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
- config: `abi` index config field has been removed; add `evm.etherscan` datasource(s) to the `datasources` list instead.

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

- evm.etherscan: Raise `AbiNotAvailableError` when contract is not verified.
- cli: Fixed incorrect indexer status logging.
- evm.node: Fixed memory leak when using realtime subscriptions.
- evm.node: Fixed processing chain reorgs.
- evm.node: Respect `http.batch_size` when fetching block headers.

### Performance

- hasura: Apply table customizations in a single request.
- performance: Collect hit/miss stats for cached models.
- performance: Decrease main loop and node polling intervals.
- performance: Drop caches when all indexes have reached realtime.

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

- evm.etherscan: Fixed handling "rate limit reached" errors.
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

## [7.0.2] - 2023-10-10

### Added

- database: Added `dipdup_wipe` and `dipdup_approve` SQL functions to the schema.

### Fixed

- cli: Fixed `schema wipe` command for SQLite databases.
- tezos.tzkt: Fixed regression in `get_transactions` method pagination.

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

## [7.0.0rc5] - 2023-09-06

### Fixed

- evm.subsquid: Create a separate aiohttp session for each worker.
- evm.subsquid.events: Sync to `last_level` if specified in config.
- evm.node: Set `timestamp` field to the block timestamp.

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

## [7.0.0rc2] - 2023-07-26

### Fixed

- package: Create missing files from project base on init.
- package: Update replay.yaml on init.
- demos: Don't include database config in root config.

## [7.0.0rc1] - 2023-07-21

### Added

- evm.etherscan: Added `evm.etherscan` datasource to fetch ABIs from Etherscan.
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

<!-- Links -->
[keep a changelog]: https://keepachangelog.com/en/1.0.0/
[semantic versioning]: https://semver.org/spec/v2.0.0.html

<!-- Versions -->
[Unreleased]: https://github.com/dipdup-io/dipdup/compare/8.5.1...HEAD
[8.5.1]: https://github.com/dipdup-io/dipdup/compare/8.5.0...8.5.1
[8.5.0]: https://github.com/dipdup-io/dipdup/compare/8.4.3...8.5.0
[8.4.3]: https://github.com/dipdup-io/dipdup/compare/8.4.2...8.4.3
[8.4.2]: https://github.com/dipdup-io/dipdup/compare/8.4.1...8.4.2
[8.4.1]: https://github.com/dipdup-io/dipdup/compare/8.4.0...8.4.1
[8.4.0]: https://github.com/dipdup-io/dipdup/compare/8.3.3...8.4.0
[8.3.3]: https://github.com/dipdup-io/dipdup/compare/8.3.2...8.3.3
[8.3.2]: https://github.com/dipdup-io/dipdup/compare/8.3.1...8.3.2
[8.3.1]: https://github.com/dipdup-io/dipdup/compare/8.3.0...8.3.1
[8.3.0]: https://github.com/dipdup-io/dipdup/compare/8.2.2...8.3.0
[8.2.2]: https://github.com/dipdup-io/dipdup/compare/8.2.1...8.2.2
[8.2.1]: https://github.com/dipdup-io/dipdup/compare/8.2.0...8.2.1
[8.2.0]: https://github.com/dipdup-io/dipdup/compare/8.2.0rc1...8.2.0
[8.2.0rc1]: https://github.com/dipdup-io/dipdup/compare/8.1.4...8.2.0rc1
[8.1.4]: https://github.com/dipdup-io/dipdup/compare/8.1.3...8.1.4
[8.1.3]: https://github.com/dipdup-io/dipdup/compare/8.1.2...8.1.3
[8.1.2]: https://github.com/dipdup-io/dipdup/compare/8.1.1...8.1.2
[8.1.1]: https://github.com/dipdup-io/dipdup/compare/8.1.0...8.1.1
[8.1.0]: https://github.com/dipdup-io/dipdup/compare/8.0.0...8.1.0
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
[7.4.0]: https://github.com/dipdup-io/dipdup/compare/7.3.2...7.4.0
[7.3.2]: https://github.com/dipdup-io/dipdup/compare/7.3.1...7.3.2
[7.3.1]: https://github.com/dipdup-io/dipdup/compare/7.3.0...7.3.1
[7.3.0]: https://github.com/dipdup-io/dipdup/compare/7.2.2...7.3.0
[7.2.2]: https://github.com/dipdup-io/dipdup/compare/7.2.1...7.2.2
[7.2.1]: https://github.com/dipdup-io/dipdup/compare/7.2.0...7.2.1
[7.2.0]: https://github.com/dipdup-io/dipdup/compare/7.1.1...7.2.0
[7.1.1]: https://github.com/dipdup-io/dipdup/compare/7.1.0...7.1.1
[7.1.0]: https://github.com/dipdup-io/dipdup/compare/7.0.2...7.1.0
[7.0.2]: https://github.com/dipdup-io/dipdup/compare/7.0.1...7.0.2
[7.0.1]: https://github.com/dipdup-io/dipdup/compare/7.0.0...7.0.1
[7.0.0]: https://github.com/dipdup-io/dipdup/compare/7.0.0rc5...7.0.0
[7.0.0rc5]: https://github.com/dipdup-io/dipdup/compare/7.0.0rc4...7.0.0rc5
[7.0.0rc4]: https://github.com/dipdup-io/dipdup/compare/7.0.0rc3...7.0.0rc4
[7.0.0rc3]: https://github.com/dipdup-io/dipdup/compare/7.0.0rc2...7.0.0rc3
[7.0.0rc2]: https://github.com/dipdup-io/dipdup/compare/7.0.0rc1...7.0.0rc2
[7.0.0rc1]: https://github.com/dipdup-io/dipdup/compare/6.5.9...7.0.0rc1
