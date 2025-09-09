<!-- markdownlint-disable first-line-h1 -->
| name | description |
|-|-|
| `DIPDUP_DEBUG` | Enable debug logging and additional checks |
| `DIPDUP_JSON_LOG` | Print logs in JSON format |
| `DIPDUP_LOW_MEMORY` | Reduce the size of caches and buffers for low-memory environments (only for debugging!) |
| `DIPDUP_MIGRATIONS` | Enable migrations with `aerich` |
| `DIPDUP_NEXT` | Enable experimental and breaking features from the next major release |
| `DIPDUP_NO_LINTER` | Don't format and lint generated files with ruff |
| `DIPDUP_NO_BASE` | Don't recreate files from base project template |
| `DIPDUP_NO_HOOKS` | Don't run hooks, both internal and user-defined |
| `DIPDUP_NO_SYMLINK` | Don't create magic symlink in the package root even when used as cwd |
| `DIPDUP_NO_VERSION_CHECK` | Disable warning about running unstable or out-of-date DipDup version |
| `DIPDUP_PACKAGE_PATH` | Disable package discovery and use the specified path |
| `DIPDUP_REPLAY_PATH` | Path to datasource replay files; used in tests (dev only) |
| `DIPDUP_TEST` | Running in tests (disables Sentry and some checks) |
