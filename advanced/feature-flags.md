# Feature flags

## Early realtime

|cli|config|is table|
|-|-|-|
|`run --early-realtime`|`advanced.early_realtime`|✅|

When this flag is not set, DipDup enters sync state twice: before and after establishing a realtime connection. Let's consider two different scenarios:

1. Indexing ten contracts with 10k+ operations each. Initial indexing could take several hours. There is no need to accumulate incoming operations since resync time after establishing a realtime connection depends on contracts number, thus taking a negligible amount of time.

2. Indexing 10k+ contracts with ten operations each. Both initial sync and resync will take a while. But the number of operations received during this time won't affect RAM consumption much.

## Merge subscriptions

|cli|config|is stable|
|-|-|-|
|`run --merge-subscriptions`|`advanced.merge_subscriptions`|✅|

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

Subscribe to all operations/big map diffs during realtime indexing.

## Postpone jobs

|cli|config|is stable|
|-|-|-|
|`run --postpone-jobs`|`advanced.postpone_jobs`|✅|

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

Do not start the job scheduler until all indexes are synchronized.
