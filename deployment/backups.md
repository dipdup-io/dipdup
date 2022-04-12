# Backup and restore

DipDup has no built-in functionality to backup and restore database at the moment. Good news is that DipDup indexes are **fully atomic**. That means you can perform backup with regular `psql`/`pgdump` regardless of the DipDup state.

This page contains several recipes for backup/restore.

## Scheduled backup to S3

This example is for Swarm deployments. We use this solution to backup our services in production. Adapt it to your needs if needed.

```yaml
version: "3.8"
services:
  indexer:
    ...
  db:
    ...
  hasura:
    ...

  backuper:
    image: ghcr.io/dipdup-net/postgres-s3-backup:master
    environment:
      - S3_ENDPOINT=${S3_ENDPOINT:-https://fra1.digitaloceanspaces.com}
      - S3_ACCESS_KEY_ID=${S3_ACCESS_KEY_ID}
      - S3_SECRET_ACCESS_KEY=${S3_SECRET_ACCESS_KEY}
      - S3_BUCKET=dipdup
      - S3_PATH=dipdup
      - S3_FILENAME=${SERVICE}-postgres
      - PG_BACKUP_FILE=${PG_BACKUP_FILE}
      - PG_BACKUP_ACTION=${PG_BACKUP_ACTION:-dump}
      - PG_RESTORE_JOBS=${PG_RESTORE_JOBS:-8}
      - POSTGRES_USER=${POSTGRES_USER:-dipdup}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}
      - POSTGRES_DB=${POSTGRES_DB:-dipdup}
      - POSTGRES_HOST=${POSTGRES_HOST:-db}
      - HEARTBEAT_URI=${HEARTBEAT_URI}
      - SCHEDULE=${SCHEDULE}
    deploy:
      mode: replicated
      replicas: ${BACKUP_ENABLED:-0}
      restart_policy:
        condition: on-failure
        delay: 10s
        max_attempts: 5
        window: 120s
      placement: *placement
    networks:
      - internal
    logging: *logging

```

## Automatic restore on rollback

This awesome code was contributed by [@852Kerfunkle](https://github.com/852Kerfunkle), author of [tz1and](https://github.com/tz1and/) project.

`<project>/backups.py`

```python
...

def backup(level: int, database_config: PostgresDatabaseConfig):
    ...

    with open('backup.sql', 'wb') as f:
        try:
            err_buf = StringIO()
            pg_dump('-d', f'postgresql://{database_config.user}:{database_config.password}@{database_config.host}:{database_config.port}/{database_config.database}', '--clean',
                '-n', database_config.schema_name, _out=f, _err=err_buf) #, '-E', 'UTF8'
        except ErrorReturnCode:
            err = err_buf.getvalue()
            _logger.error(f'Database backup failed: {err}')


def restore(level: int, database_config: PostgresDatabaseConfig):
    ...

    with open('backup.sql', 'r') as f:
        try:
            err_buf = StringIO()
            psql('-d', f'postgresql://{database_config.user}:{database_config.password}@{database_config.host}:{database_config.port}/{database_config.database}',
                '-n', database_config.schema_name, _in=f, _err=err_buf)
        except ErrorReturnCode:
            err = err_buf.getvalue()
            _logger.error(f'Database restore failed: {err}')
            raise Exception("Failed to restore")

def get_available_backups():
    ...


def delete_old_backups():
    ...
```

`<project>/hooks/on_rollback.py`

```python
...

async def on_rollback(
    ctx: HookContext,
    datasource: Datasource,
    from_level: int,
    to_level: int,
) -> None:
    await ctx.execute_sql('on_rollback')

    database_config: Union[SqliteDatabaseConfig, PostgresDatabaseConfig] = ctx.config.database

    # if not a postgres db, reindex.
    if database_config.kind != "postgres":
        await ctx.reindex(ReindexingReason.ROLLBACK)

    available_levels = backups.get_available_backups()

    # if no backups available, reindex
    if not available_levels:
        await ctx.reindex(ReindexingReason.ROLLBACK)

    # find the right level. ie the on that's closest to to_level
    chosen_level = 0
    for level in available_levels:
        if level <= to_level and level > chosen_level:
            chosen_level = level

    # try to restore or reindex
    try:
        backups.restore(chosen_level, database_config)
        await ctx.restart()
    except Exception:
        await ctx.reindex(ReindexingReason.ROLLBACK)
```

`<project>/hooks/run_backups.py`

```python
...

async def run_backups(
    ctx: HookContext,
) -> None:
    database_config: Union[SqliteDatabaseConfig, PostgresDatabaseConfig] = ctx.config.database

    if database_config.kind != "postgres":
        return

    level = ctx.get_tzkt_datasource("tzkt_mainnet")._level.get(MessageType.head)

    if level is None:
        return

    backups.backup(level, database_config)
    backups.delete_old_backups()
```

`<project>/hooks/simulate_reorg.py`

```python
...

async def simulate_reorg(
    ctx: HookContext
) -> None:
    level = ctx.get_tzkt_datasource("tzkt_mainnet")._level.get(MessageType.head)

    if level:
        await ctx.fire_hook("on_rollback", wait=True, datasource=ctx.get_tzkt_datasource("tzkt_mainnet"), from_level=level, to_level=level-2)
```
