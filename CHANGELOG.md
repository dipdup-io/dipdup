# Changelog

## [unreleased]

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
