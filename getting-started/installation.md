# Installation

This page covers the installation of DipDup in differens environments.

## Host requirements

A Linux environment with Python 3.10+ installed is required to use DipDup.

Minimum hardware requirements are 256 MB RAM, 1 CPU core, and some disk space for the database.

### Non-Linux environments

Other UNIX-like systems (MacOS, FreeBSD etc.) should work, however not supported officially.

DipDup currently doesn't work in Windows environments due to incompabilities in libraries it depends on. Please use WSL or Docker.

We aim to improve cross-platform compatibility in the future releases.

> 🤓 **SEE ALSO**
>
> * [5.6. Improving performance](advanced/performance/)
> * [What is the Windows Subsystem for Linux?](https://docs.microsoft.com/en-us/windows/wsl/about)

## Local installation

To begin with, create a new directory for your project and enter it. Now choose one way of managing virtual environment:

### Poetry (recommended)

Initialize a new PEP 518 project and add DipDip to dependencies.

```shell
poetry init -n
poetry add dipdup
```

### pip

Create a new virtual environment and install DipDup in it.

```shell
python -m venv .venv
source .venv/bin/activate
pip install dipdup
```

## Other options

> 🤓 **SEE ALSO**
>
> * [8.2. Building Docker images](../deployment/docker.md)
> * [8.3. Deploying with docker-compose](../deployment/docker-compose.md)
> * [8.4. Deploying with Docker Swarm](../deployment/swarm.md)
