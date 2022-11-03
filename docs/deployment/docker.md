# Running in Docker

## Base images

DipDup provides multiple prebuilt images for different environments hosted on [Docker Hub](https://hub.docker.com/r/dipdup/dipdup). Choose the one according to your needs from the table below.

| | default | pytezos | slim |
| - | :-: | :-: | :-: |
| base image | `python:3.10-slim` | `python:3.10-slim` | `python:3.10-alpine` |
| platforms | `amd64`, `arm64` | `amd64`, `arm64` | `amd64`, `arm64` |
| latest tag | `{{ cookiecutter.dipdup_version }}` | `{{ cookiecutter.dipdup_version }}-pytezos` | `{{ cookiecutter.dipdup_version }}-slim` |
| image size | 352M | 481M | 136M | <!-- TODO: Possibly outdated -->
| `dipdup init` command | ✅ | ✅ | ❌ |
| `git` and `poetry` included | ✅ | ✅ | ❌ |
| PyTezos included | ❌ | ✅ | ❌

The default DipDup image is suitable for development and testing. It also includes some tools to make package management easier. If unsure, use this image.

### `-slim` image

Based on Alpine Linux, this image is much smaller than the default one. Also, it doesn't include codegen functionality (`init` command, unlikely to be useful in production).

### `-pytezos` image

The only difference with the default image is the pre-installed PyTezos library, the same as `pip install dipdup -E pytezos`. DipDup doesn't provide any further PyPoetry integration. Having some patience, you can build a trading robot or something like that using this image. I don't know if anyone is using it. If you're the one on them, please let us know!

### Nightly builds (ghcr.io)

In addition to [Docker Hub](https://hub.docker.com/r/dipdup/dipdup) we also publish images on [GitHub Packages](https://github.com/dipdup-net/dipdup/pkgs/container/dipdup). Builds are triggered on push to any branch for developers' convenience. Do not use this registry in production!

```Dockerfile
# Slim image for `aux/arm64` branch
FROM ghcr.io/dipdup-net/dipdup:aux-arm64-slim
```

## Writing Dockerfile

Start with creating `.dockerignore` for your project if it's missing.

```text
{{ #include ../../src/dipdup/projects/base/.dockerignore.j2 }}
```

A typical Dockerfile looks like this:

```Dockerfile
{{ #include ../../src/dipdup/projects/base/Dockerfile.j2 }}
```

Note that Poetry integration is not available in the slim image.

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

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

Example stack:

```yaml
{{ #include ../../src/dipdup/projects/base/docker-compose.swarm.yml.j2 }}
```
