# Docker compose

Make sure you have [docker](https://docs.docker.com/get-docker/) and [docker-compose](https://docs.docker.com/compose/install/) installed.

**Step 1.** Create `Dockerfile` with the following content:

Assuming you are using [poetry](https://python-poetry.org/) for managing the project:

```dockerfile
FROM python:3.9-slim-buster

RUN pip install poetry

WORKDIR /demo
COPY poetry.lock pyproject.toml /demo/

RUN poetry config virtualenvs.create false && poetry install --no-dev

COPY . /demo

ENTRYPOINT ["poetry", "run", "dipdup"]
CMD ["-c", "dipdup.yml", "run"]
```

 **Step 2.** Create `docker-compose.yml` with the following sections:

```yaml
version: "3.8"

services:
  indexer:
    build: .
    depends_on:
      - db
      - hasura
    restart: "no"
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}
      - ADMIN_SECRET=${ADMIN_SECRET:-changeme}

  db:
    image: postgres:13
    restart: always
    volumes:
      - db:/var/lib/postgres/data
    environment: 
      - POSTGRES_USER=dipdup
      - POSTGRES_DB=dipdup
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  hasura:
    image: hasura/graphql-engine:v2.0.1
    ports:
      - 127.0.0.1:42000:8080
    depends_on:
      - db
    restart: always
    environment:
      - HASURA_GRAPHQL_DATABASE_URL=postgres://dipdup:${POSTGRES_PASSWORD:-changeme}@db:5432/dipdup
      - HASURA_GRAPHQL_ENABLE_CONSOLE=false
      - HASURA_GRAPHQL_DEV_MODE=false
      - HASURA_GRAPHQL_ENABLED_LOG_TYPES=startup, http-log, webhook-log, websocket-log, query-log
      - HASURA_GRAPHQL_ADMIN_SECRET=${ADMIN_SECRET:-changeme}
      - HASURA_GRAPHQL_UNAUTHORIZED_ROLE=user
  
volumes:
  db:
```

{% hint style="info" %}
Recall that environment variables are expanded in the DipDup config file — in our case we are forwarding Postgres password and Hasura secret.
{% endhint %}

**Step 3.** Update `dipdup.yml` \(or create a dedicated config for docker deployment\):

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

Note the hostnames \(will be resolved in the docker network\) and environment variables \(will be expanded by DipDup\).

**Step 4.** Build and run the containers:

```text
docker-compose up -d --build
```

We recommend [lazydocker](https://github.com/jesseduffield/lazydocker) for monitoring your application.
