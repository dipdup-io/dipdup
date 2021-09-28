# Changelog

## [unreleased]

### Added

* Human-readable `CHANGELOG.md` 🕺
* `--forbid-reindexing` option added to `dipdup run` command. If this flag is set DipDup will raise `ReindexingRequiredError` when reindexing is triggered for any reason. A database won't be truncated. To continue indexing with existing database run `UPDATE dipdup_schema SET reindex = NULL;`

### Changed

* `Index.head` relation removed. `dipdup_head` now contains the latest 10 blocks received by each datasource.

### Fixed

* Removed unnecessary calls to TzKT API.
* Fixed removal of PostgreSQL extensions (`timescaledb`, `pgcrypto`) by function `truncate_database` triggered on reindex.
* Fixed creation of missing project package on `init`.
* Fixed invalid handler callbacks generated on `init`.
* Fixed detection of existing types in the project.
* Fixed race condition caused by event emitter concurrency.
* Capture unknown exceptions with Sentry before wrapping to `DipDupError`.
* Fixed job scheduler start delay.

## 3.0.1 - 2021-09-24

### Added

* Added `get_quote` and `get_quotes` methods to `TzKTDatasource`.

### Fixed

* Defer spawning index datasources until initial sync is complete. It helps to mitigate some WebSocket-related crashes, but initial sync is a bit slower now.
* Fixed possible race conditions in `TzKTDatasource`.
* Start `jobs` scheduler after all indexes sync with a current head to speed up indexing.
