# Backup and restore

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

PostgreSQL S3 backup recipe for Swarm:

```docker-compose
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
