# Running in Docker

## Base images

DipDup provides multiple prebuilt images for different environments hosted on Docker Hub. Choose the one according to your needs from the table below.

| | default | pytezos | slim |
| - | :-: | :-: | :-: |
| base image | `python:3.10-slim-buster` | `python:3.10-slim-buster` | `python:3.10-alpine` |
| platforms | `amd64`, `arm64` | `amd64`, `arm64` | `amd64`, `arm64` |
| latest tag | `dipdup/dipdup:6` | `dipdup/dipdup:6-pytezos` | `dipdup/dipdup:6-slim` |
| image size | 355M | 646M | 147M |
| `dipdup init` command | ✅ | ✅ | ❌ |
| `git`, and `poetry` included | ✅ | ✅ | ❌ |
| PyTezos included | ❌ | ✅ | ❌

Default DipDup image is suitable for development and testing. It includes some developments tools to make package management easier. If unsure, use this image.

### `-slim` image

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

### `-pytezos` image

The only difference with the default image is pre-installed PyTezos library, the same as `pip install dipdup -E pytezos`. DipDup doesn't provide any further PyPoetry integration. Having some patience you can build a trading robot or something like that using this image. I don't know if anyone is using it. If you're the one on them, please let us know!

### GitHub Container Registry



## Writing Dockerfile

Start with creating `.dockerignore` for your project if it's missing.

```text
# Ignore all
*

# Add build files
!Makefile
!pyproject.toml
!poetry.lock
!README.md

# Add code
!generic_dex

# Add configs
!*.yml

# Ignore caches
**/.mypy_cache
**/__pycache__
```

A typical Dockerfile for default and pytezos images looks like this:

```Dockerfile
FROM dipdup/dipdup:6
# FROM dipdup/dipdup:6-pytezos

# Uncomment if you have additional dependencies in pyproject.toml
# COPY pyproject.toml poetry.lock ./
# RUN inject_pyproject

COPY . .
```

Slim image doesn't provide poetry integration, so if your project has additional dependencies, you need to install them manually.

```Dockerfile
FROM dipdup/dipdup:6
# FROM dipdup/dipdup:6-pytezos

# Installing additional dependencies
# COPY requirements.txt ./
# /usr/local/bin/pip install --prefix /opt/dipdup --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY . .
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
