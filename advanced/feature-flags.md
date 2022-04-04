# Feature flags

Feature flags allow users to modify some system-wide tunables that affect behaviour of the whole framework. These options are either experimental or unsuitable for generic configurations.

| `run` command option | config path | is stable |
| - | - | - |
| `--early-realtime` | `advanced.early_realtime` | ✅ |
| `--merge-subscriptions` | `advanced.merge_subscriptions` | ✅ |
| `--postpone-jobs` | `advanced.postpone_jobs` | ✅ |
| `--metadata-interface` | `advanced.metadata_interface` | ✅ |

Good practice is to use set feature flags in environment-specific config files.

## Early realtime

By default, DipDup enters sync state twice: before and after establishing a realtime connection. This flag allows to start collecting realtime messages while sync is in progress, right after indexes load.

Let's consider two scenarios:

1. Indexing 10 contracts with 10 000 operations each. Initial indexing could take several hours. There is no need to accumulate incoming operations since resync time after establishing a realtime connection depends on contracts number, thus taking a negligible amount of time.

2. Indexing 10 000 contracts with 10 operations each. Both initial sync and resync will take a while. But the number of operations received during this time won't affect RAM consumption much.

If you have not strict RAM constraints, it's recommended to enable this flag. faster indexing times and to decrease load on tzkt api.

## Merge subscriptions

Subscribe to all operations/big map diffs during realtime indexing. IncreaseX at the cost of Y.

size, with early

## Postpone jobs

Do not start the job scheduler until all indexes are synchronized. `on_synchronized`

save database iops

## Metadata interface

tables created

w/o flag will be ignored