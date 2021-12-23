# Installation

This page covers the installation of DipDup in local environments. See [7.2. Building Docker images](../deployment/docker.md) to learn how to use DipDup in containers.

## Host requirements

A Linux environment with Python 3.8+ installed is required to use DipDup.

Minimum hardware requirements are 256 MB RAM, 1 CPU core, and some disk space for the database.

## Local installation

To begin with, create a new directory for your project and enter it. Now choose one:

### poetry (recommended)

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
