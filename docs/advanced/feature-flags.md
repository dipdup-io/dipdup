# Feature flags

Feature flags set in `advanced` config section allow users to modify parameters that affect the behavior of the whole framework. Choosing the right combination of flags for an indexer project can improve performance, reduce RAM consumption, or enable useful features.

| flag                  | description                                                          |
| --------------------- | -------------------------------------------------------------------- |
| `crash_reporting`     | Enable sending crash reports to the Baking Bad team                  |
| `early_realtime`      | Start collecting realtime messages while sync is in progress         |
| `merge_subscriptions` | Subscribe to all operations/big map diffs during realtime indexing   |
| `metadata_interface`  | Enable contract and token metadata interfaces                        |
| `postpone_jobs`       | Do not start the job scheduler until all indexes are synchronized    |
| `skip_version_check`  | Disable warning about running unstable or out-of-date DipDup version |

## Crash reporting

Enables sending crash reports to the Baking Bad team. This is **disabled by default**. You can inspect crash dumps saved as `/tmp/dipdup/crashdumps/XXXXXXX.json` before enabling this option.

```admonish info title="See Also"
* {{ #summary troubleshooting.md}}
```

## Early realtime

By default, DipDup enters a sync state twice: before and after establishing a realtime connection. This flag allows collecting realtime messages while the sync is in progress, right after indexes load.

Let's consider two scenarios:

1. Indexing 10 contracts with 10 000 operations each. Initial indexing could take several hours. There is no need to accumulate incoming operations since resync time after establishing a realtime connection depends on the contract number, thus taking a negligible amount of time.

2. Indexing 10 000 contracts with 10 operations each. Both initial sync and resync will take a while. But the number of operations received during this time won't affect RAM consumption much.

If you do not have strict RAM constraints, it's recommended to enable this flag. You'll get faster indexing times and decreased load on TzKT API.

## Merge subscriptions

Subscribe to all operations/big map diffs during realtime indexing instead of separate channels. This flag helps to avoid the 10.000 subscription limit of TzKT and speed up processing. The downside is an increased RAM consumption during sync, especially if `early_realtime` flag is enabled too.

## Metadata interface

Without this flag calling `ctx.update_contract_metadata` and `ctx.update_token_metadata` methods will have no effect. Corresponding internal tables are created on reindexing in any way.

## Postpone jobs

Do not start the job scheduler until all indexes are synchronized. If your jobs perform some calculations that make sense only after the indexer has reached realtime, this toggle can save you some IOPS.

## Skip version check

Disables warning about running unstable or out-of-date DipDup version.

## Internal environment variables

DipDup uses multiple environment variables internally. They read once on process start and usually do not change during runtime. Some variables modify the framework's behavior, while others are informational.

Please note that they are not currently a part of the public API and can be changed without notice.

| env variable          | module path               | description                                                           |
| --------------------- | ------------------------- | --------------------------------------------------------------------- |
| `DIPDUP_CI`           | `dipdup.env.CI`           | Running in GitHub Actions                                             |
| `DIPDUP_DOCKER`       | `dipdup.env.DOCKER`       | Running in Docker                                                     |
| `DIPDUP_NEXT`         | `dipdup.env.NEXT`         | Enable features thar require schema changes                           |
| `DIPDUP_PACKAGE_PATH` | `dipdup.env.PACKAGE_PATH` | Path to the currently used package                                    |
| `DIPDUP_REPLAY_PATH`  | `dipdup.env.REPLAY_PATH`  | Path to datasource replay files; used in tests                        |
| `DIPDUP_TEST`         | `dipdup.env.TEST`         | Running in pytest                                                     |

`DIPDUP_NEXT` flag will give you the picture of what's coming in the next major release, but enabling it on existing schema will trigger a reindexing.
