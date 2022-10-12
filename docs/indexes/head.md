# `head` index

This very simple index provides metadata of the latest block when it's baked. Only realtime data is processed; the synchronization stage is skipped for this index.

```yaml
{{ #include ../../demos/demo-head/dipdup.yml }}
```

Head index callback receives `HeadBlockData` model that contains only basic info; no operations are included. Being useless by itself, this index is helpful for monitoring and cron-like tasks. You can define multiple indexes for each datasource used.

Subscription to the head channel is enabled by default, even if no head indexes are defined. Each time the block is baked, the `dipdup_head` table is updated per datasource. Use it to ensure that both index datasource and underlying blockchain are up and running.

> 💡 **SEE ALSO**
>
> * {{ #summary deployment/monitoring.md}}
