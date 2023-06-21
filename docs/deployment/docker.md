# Running in Docker

DipDup provides prebuilt Docker images hosted on [Docker Hub](https://hub.docker.com/r/dipdup/dipdup). You can use them as is or build custom images based on them.

Some defails about the published images:

|                         |                                                   |
| ----------------------- |:-------------------------------------------------:|
| Latest tag              | `dipdup/dipdup:{{ project.dipdup_version }}` |
| Base image              |             `python:3.11-slim-buster`             |
| Supported architectures |                  `amd64`, `arm64`                 |
| Size                    |                     `~ 400 MB`                    |
| User                    |                      `dipdup`                     |
| UID                     |                       `1000`                      |
| Home directory          |                   `/home/dipdup`                  |
| Working directory       |                   `/home/dipdup`                  |
| Entrypoint              |                      `dipdup`                     |
| Venv                    |                   `/opt/dipdup`                   |

## Usage

To run DipDup in container, you need to copy or mount your project directory and config file to the container.

Given your project source code is in `src` directory and config file is `dipdup.yml`, you can run DipDup container using bind mounts with the following command:

```shell
docker run \
  -v ./dipdup.yml:/home/dipdup/dipdup.yml \
  -v ./src:/home/dipdup/src \
  dipdup/dipdup:{{ project.dipdup_version }}
```

If you're using SQLite database, you can also mount it as a volume:

```shell
docker run \
  -v ./dipdup.yml:/home/dipdup/dipdup.yml \
  -v ./src:/home/dipdup/src \
  -v ./indexer.sqlite3:/home/dipdup/indexer.sqlite3 \
  dipdup/dipdup:{{ project.dipdup_version }}
```

## Building custom image

Start with creating `.dockerignore` for your project if it's missing.

```text
{{ #include ../../src/dipdup/projects/base/.dockerignore.j2 }}
```

Then copy your code and config file to the image:

```Dockerfile
{{ #include ../../src/dipdup/projects/base/deploy/Dockerfile.j2 }}
```

If you need to install additional Python dependencies, just call pip directly during the build stage:

```Dockerfile
RUN pip install --no-cache -r requirements.txt
```

## Nightly builds (ghcr.io)

In addition to [Docker Hub](https://hub.docker.com/r/dipdup/dipdup) we also publish images on [GitHub Container Registry](https://github.com/dipdup-io/dipdup/pkgs/container/dipdup) aka GHCR. Builds are triggered on push to any branch for developers' convenience. Do not use nightlies in production!

```Dockerfile
# Latest image for default branch `next`
FROM ghcr.io/dipdup-io/dipdup:next
```

## Deploying with `docker-compose`

Here's an example `docker-compose.yml` file:

```yaml
{{ #include ../../src/dipdup/projects/base/deploy/compose.yaml.j2 }}
```

Environment variables are expanded in the DipDup config file; PostgreSQL password and Hasura secret are forwarded from host environment in this example.

You can create a separate `dipdup.<environment>.yml` file for this stack to apply environment-specific config overrides:

```yaml
{{ #include ../../src/dipdup/projects/base/configs/compose.yml.j2 }}
```

Then modify command in `docker-compose.yml`:

```yaml
services:
  dipdup:
    command: ["dipdup", "-c", "dipdup.yml", "-c", "dipdup.prod.yml", "run"]
    ...
```

Note the hostnames (resolved in the docker network) and environment variables (expanded by DipDup).

Build and run the containers:

```shell
docker-compose up -d --build
```

Try [lazydocker](https://github.com/jesseduffield/lazydocker) tool to manage Docker containers interactively.

## Deploying with Docker Swarm

```admonish warning title=""
This page or paragraph is yet to be written. Come back later.
```

Example stack:

```yaml
{{ #include ../../src/dipdup/projects/base/deploy/swarm.compose.yaml.j2 }}
```
