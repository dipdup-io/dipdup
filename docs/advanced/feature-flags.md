# Feature flags

Feature flags allow users to modify some system-wide tunables that affect the behavior of the whole framework. These options are either experimental or unsuitable for generic configurations.

A good practice is to use set feature flags in environment-specific config files.

```yaml
advanced:
  early_realtime: False
  merge_subscriptions: False
  postpone_jobs: False
  metadata_interface: False
  skip_version_check: False
  crash_reporting: False
```

## Early realtime

By default, DipDup enters a sync state twice: before and after establishing a realtime connection. This flag allows starting collecting realtime messages while sync is in progress, right after indexes load.

Let's consider two scenarios:

1. Indexing 10 contracts with 10 000 operations each. Initial indexing could take several hours. There is no need to accumulate incoming operations since resync time after establishing a realtime connection depends on the contract number, thus taking a negligible amount of time.

2. Indexing 10 000 contracts with 10 operations each. Both initial sync and resync will take a while. But the number of operations received during this time won't affect RAM consumption much.

If you do not have strict RAM constraints, it's recommended to enable this flag. You'll get faster indexing times and decreased load on TzKT API.

## Merge subscriptions

Subscribe to all operations/big map diffs during realtime indexing instead of separate channels. This flag helps to avoid the 10.000 subscription limit of TzKT and speed up processing. The downside is an increased RAM consumption during sync, especially if `early_realtimm` flag is enabled too.

## Postpone jobs

Do not start the job scheduler until all indexes are synchronized. If your jobs perform some calculations that make sense only after indexing is fully finished, this toggle can save you some IOPS.

## Metadata interface

Without this flag calling `ctx.update_contract_metadata` and `ctx.update_token_metadata` will make no effect. Corresponding internal tables are created on reindexing in any way.

## Skip version check

Disables warning about running unstable or out-of-date DipDup version.

## Crash reporting

Enables sending crash reports to the Baking Bad team. This is **disabled by default**. You can inspect crash dumps saved as `/tmp/dipdup/crashdumps/XXXXXXX.json` before enabling this option.
