# Changelog

## [unreleased]

### Added

* Human-readable `CHANGELOG.md` 🕺
* `--forbid-reindexing` option added to `dipdup run` command. When this flag is set DipDup will raise `ReindexingRequiredError` instead of truncating database when reindexing is triggered for any reason.

### Fixed

* Removed unnecessary calls to TzKT API during the partial sync.
* Fixed removal of PostgreSQL extensions (`timescaledb`, `pgcrypto`) by function `truncate_database` triggered on reindex.
* Fixed updating relation between index and head in DB.
* Fixed creation of missing project package on `init`.
* Fixed invalid handler callbacks generated on `init`.
* Fixed detection of existing types in the project.

## 3.0.1 - 2021-09-24

### Added

* Added `get_quote` and `get_quotes` methods to `TzKTDatasource`.

### Fixed

* Defer spawning index datasources until initial sync is complete. It helps to mitigate some WebSocket-related crashes, but initial sync is a bit slower now.
* Fixed possible race conditions in `TzKTDatasource`.
* Start `jobs` scheduler after all indexes sync with a current head to speed up indexing.
