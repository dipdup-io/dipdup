# Running in Docker

## Building images

```Dockerfile
FROM dipdup/dipdup:6.0

# Uncomment if you have additional dependencies in pyproject.toml
# COPY pyproject.toml poetry.lock ./
# RUN inject_pyproject

COPY indexer indexer
COPY dipdup.yml dipdup.prod.yml ./
```

## Deploying with `docker-compose`

Make sure you have [docker](https://docs.docker.com/get-docker/) run and [docker-compose](https://docs.docker.com/compose/install/) installed.

Example `docker-compose.yml` file:

```yaml
version: "3.8"

services:
  indexer:
    build: .
    depends_on:
      - db
    command: ["-c", "dipdup.yml", "-c", "dipdup.prod.yml", "run"]
    restart: "no"
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}
      - ADMIN_SECRET=${ADMIN_SECRET:-changeme}
    volumes:
      - ./dipdup.yml:/home/dipdup/dipdup.yml
      - ./dipdup.prod.yml:/home/dipdup/dipdup.prod.yml
      - ./indexer:/home/dipdup/indexer
    ports:
      - 127.0.0.1:9000:9000

  db:
    image: timescale/timescaledb:latest-pg13
    ports:
      - 127.0.0.1:5432:5432
    volumes:
      - db:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=dipdup
      - POSTGRES_DB=dipdup
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      mode: replicated
      replicas: 1

  hasura:
    image: hasura/graphql-engine:v2.8.3
    ports:
      - 127.0.0.1:8080:8080
    depends_on:
      - db
    restart: always
    environment:
      - HASURA_GRAPHQL_DATABASE_URL=postgres://dipdup:${POSTGRES_PASSWORD:-changeme}@db:5432/dipdup
      - HASURA_GRAPHQL_ENABLE_CONSOLE=true
      - HASURA_GRAPHQL_DEV_MODE=true
      - HASURA_GRAPHQL_ENABLED_LOG_TYPES=startup, http-log, webhook-log, websocket-log, query-log
      - HASURA_GRAPHQL_ADMIN_SECRET=${ADMIN_SECRET:-changeme}
      - HASURA_GRAPHQL_UNAUTHORIZED_ROLE=user
      - HASURA_GRAPHQL_STRINGIFY_NUMERIC_TYPES=true

volumes:
  db:
```

Environment variables are expanded in the DipDup config file; Postgres password and Hasura secret are forwarded in this example.

Create a separate `dipdup.<environment>.yml` file for this stack:

```yaml
database:
  kind: postgres
  host: db
  port: 5432
  user: dipdup
  password: ${POSTGRES_PASSWORD:-changeme}
  database: dipdup
  schema_name: demo

hasura:
  url: http://hasura:8080
  admin_secret: ${ADMIN_SECRET:-changeme}
  allow_aggregations: False
  camel_case: true
  select_limit: 100
```

Note the hostnames (resolved in the docker network) and environment variables (expanded by DipDup).

Build and run the containers:

```shell
docker-compose up -d --build
```

We recommend [lazydocker](https://github.com/jesseduffield/lazydocker) for monitoring your application.

## Deploying with Docker Swarm

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.
