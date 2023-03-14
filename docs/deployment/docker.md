# Running in Docker

DipDup provides prebuilt Docker images hosted on [Docker Hub](https://hub.docker.com/r/dipdup/dipdup). They are based on `python:3.10-slim` image and support both amd64 and arm64 architectures.

## Usage

DipDup container runs as `dipdup` user with home directory `/home/dipdup`. The entrypoint is `dipdup` command. 

DipDup venv is placed in `/opt/dipdup` directory. The `dipdup` user has write access to `/opt/dipdup` and `/home/dipdup` directories.

Here's an example of running DipDup container with bind mounts:

```shell
docker run -it --rm \
  -v dipdup.yml:dipdup.yml \
  -v src:src \
  {{ cookiecutter.dipdup_version }}
```

## Building your own image

Start with creating `.dockerignore` for your project if it's missing.

```text
{{ #include ../../src/dipdup/projects/base/.dockerignore.j2 }}
```

Then copy your code and config file to the image:

```Dockerfile
{{ #include ../../src/dipdup/projects/base/Dockerfile.j2 }}
```

If you need to include additional Python dependencies, just call pip directly during the build stage:

```Dockerfile
RUN pip install -r requirements.txt
```

## Nightly builds (ghcr.io)

In addition to [Docker Hub](https://hub.docker.com/r/dipdup/dipdup) we also publish images on [GitHub Container Registry](https://github.com/dipdup-io/dipdup/pkgs/container/dipdup) aka GHCR. Builds are triggered on push to any branch for developers' convenience. Do not use nightlies in production!

```Dockerfile
# Latest image for `feat/foobar` branch
FROM ghcr.io/dipdup-io/dipdup:feat-foobar
```

## Writing Dockerfile

## Deploying with `docker-compose`

Make sure you have [docker](https://docs.docker.com/get-docker/) run and [docker-compose](https://docs.docker.com/compose/install/) installed.

Example `docker-compose.yml` file:

```yaml
{{ #include ../../src/dipdup/projects/base/docker-compose.yml.j2 }}
```

Environment variables are expanded in the DipDup config file; Postgres password and Hasura secret are forwarded in this example.

Create a separate `dipdup.<environment>.yml` file for this stack:

```yaml
{{ #include ../../src/dipdup/projects/base/dipdup.prod.yml.j2 }}
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
{{ #include ../../src/dipdup/projects/base/docker-compose.swarm.yml.j2 }}
```
