# Flags

## Early realtime

|cli|config|
|-|-|
|`run --early-realtime`|`advanced.early_realtime`|

When this flag is not set, DipDup enters sync state twice: before and after establishing realtime connection. Let's consider two different scenarios:

1. Indexing 10 contracts with 10k operations each. Initial indexing will take several hours. No need to accumulate fresh operations, since resync time after establishing realtime connection depends on number of contracts and will take negligible time.

2. Indexing 10k contracts with 10 operations each. Both initial sync and resync after establishing a realtime connection will take a while. But the number of operations received during this time won't affect RAM consumption much.